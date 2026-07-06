from __future__ import annotations

import hashlib
from typing import Protocol

from app.config.settings import get_settings
from app.shared.adapter_logging import logged_adapter_call


class LLMClientError(RuntimeError):
    pass


def _record_llm(mode: str, model: str, prompt_text: str, out_text: str, latency_ms: float, estimated: bool = True) -> None:
    """Record an LLM call to the observability recorder (Section 11.7). Never raises."""
    try:
        from app.observability.recorder import estimate_tokens, record_llm_call
        record_llm_call(mode, model, estimate_tokens(prompt_text), estimate_tokens(out_text),
                        latency_ms, estimated=estimated)
    except Exception:  # noqa: BLE001
        pass


def _record_llm_tokens(mode: str, model: str, in_tok, out_tok, prompt_text: str, out_text: str, latency_ms: float) -> None:
    try:
        from app.observability.recorder import estimate_tokens, record_llm_call
        record_llm_call(mode, model,
                        in_tok if in_tok is not None else estimate_tokens(prompt_text),
                        out_tok if out_tok is not None else estimate_tokens(out_text),
                        latency_ms, estimated=(in_tok is None))
    except Exception:  # noqa: BLE001
        pass


class LLMClient(Protocol):
    """Adapter interface for all LLM text generation (Section 2 of the rebuild brief).

    Services build the full prompt + context themselves so that switching between
    mock/claude/real changes nothing about prompt design — only the transport.
    """

    def generate(self, prompt: str, context: dict | None = None) -> str: ...

    def describe(self) -> dict: ...


def _render_messages(prompt: str, context: dict | None) -> tuple[str, str]:
    """Shared prompt assembly used by ALL implementations, so the exact same
    system/user content reaches mock, Claude, and Azure OpenAI."""
    context = context or {}
    system_prompt = context.get(
        "system_prompt",
        "You are the iPerform Insights & Coaching assistant for a wealth management firm. "
        "Answer using only the structured context provided. Be concise, specific and "
        "compliance-aware; cite concrete figures from the context when available.",
    )
    context_lines = [
        f"- {key}: {value}"
        for key, value in context.items()
        if key != "system_prompt" and value is not None
    ]
    user_content = prompt if not context_lines else prompt + "\n\nContext:\n" + "\n".join(context_lines)
    return system_prompt, user_content


class MockLLMClient:
    """Deterministic template generator — default driver for routine iteration.

    Uses the same assembled prompt inputs as the real clients, echoing the key
    context signals so downstream pages render meaningful, stable text without
    burning tokens on every hot reload.
    """

    @logged_adapter_call("llm")
    def generate(self, prompt: str, context: dict | None = None) -> str:
        import time as _t
        _start = _t.perf_counter()
        system_prompt, user_content = _render_messages(prompt, context)
        context = context or {}
        digest = hashlib.sha256(user_content.encode("utf-8")).hexdigest()[:8]
        signal_keys = [k for k in context if k != "system_prompt"][:6]
        signals = ", ".join(f"{k}={context[k]}" for k in signal_keys) if signal_keys else "no structured signals"
        out = (
            f"[mock-llm {digest}] {prompt.strip().splitlines()[0][:160]} — "
            f"Deterministic draft based on: {signals}. "
            "Switch LLM_CLIENT_MODE=claude to spot-check real model output with identical inputs."
        )
        _record_llm("mock", "deterministic-template", user_content, out,
                    (_t.perf_counter() - _start) * 1000, estimated=True)
        return out

    def describe(self) -> dict:
        return {"mode": "mock", "model": "deterministic-template"}


class ClaudeLLMClient:
    """Anthropic-backed client for local validation of real LLM output quality.

    Default model claude-haiku-4-5-20251001 (cheapest tier) per the rebuild brief —
    do not default to a more expensive model without being asked.
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise LLMClientError("LLM_CLIENT_MODE=claude requires ANTHROPIC_API_KEY in .env")
        import anthropic  # imported here so nothing outside this class depends on the SDK

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    @logged_adapter_call("llm")
    def generate(self, prompt: str, context: dict | None = None) -> str:
        import time as _t
        _start = _t.perf_counter()
        system_prompt, user_content = _render_messages(prompt, context)
        response = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = getattr(response, "usage", None)
        _record_llm_tokens("claude", self.model,
                           getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None),
                           user_content, text, (_t.perf_counter() - _start) * 1000)
        return text

    def describe(self) -> dict:
        return {"mode": "claude", "model": self.model}


class RealLLMClient:
    """Azure OpenAI-backed client — what runs at the client site. Uses the exact
    same assembled prompts as ClaudeLLMClient so cutover is env-only."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
            raise LLMClientError(
                "LLM_CLIENT_MODE=real requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env"
            )
        from openai import AzureOpenAI  # imported here so nothing outside this class depends on the SDK

        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self.deployment = settings.azure_openai_deployment

    @logged_adapter_call("llm")
    def generate(self, prompt: str, context: dict | None = None) -> str:
        import time as _t
        _start = _t.perf_counter()
        system_prompt, user_content = _render_messages(prompt, context)
        response = self._client.chat.completions.create(
            model=self.deployment,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        _record_llm_tokens("real", f"azure:{self.deployment}",
                           getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None),
                           user_content, text, (_t.perf_counter() - _start) * 1000)
        return text

    def describe(self) -> dict:
        return {"mode": "real", "model": f"azure:{self.deployment}"}


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Select the LLMClient per LLM_CLIENT_MODE (mock | claude | real)."""
    global _llm_client
    if _llm_client is None:
        mode = get_settings().llm_client_mode.lower()
        if mode == "mock":
            _llm_client = MockLLMClient()
        elif mode == "claude":
            _llm_client = ClaudeLLMClient()
        elif mode == "real":
            _llm_client = RealLLMClient()
        else:
            raise LLMClientError(f"Unknown LLM_CLIENT_MODE '{mode}' (expected mock|claude|real)")
    return _llm_client


def reset_llm_client() -> None:
    global _llm_client
    _llm_client = None
