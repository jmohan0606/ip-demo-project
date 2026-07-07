from __future__ import annotations

from app.agents.nodes.compliance_agent import ComplianceAgent
from app.ai.chat.context_assembler import ChatContextAssembler
from app.config.settings import get_settings
from app.guardrails.service import GuardrailService
from app.llm.client import get_llm_client
from app.models.ai_chat import ChatContextSource, ChatRequest, ChatResponse
from app.shared.ids import timestamp_id


class AiAssistantChatEngine:
    def __init__(self) -> None:
        self.context_assembler = ChatContextAssembler()
        self.llm = get_llm_client()  # Section 2 adapter: mock | claude | real | azure
        self.guardrails = GuardrailService() if get_settings().guardrails_enabled else None

    def answer(self, request: ChatRequest) -> ChatResponse:
        conversation_id = request.conversation_id or timestamp_id("conv")
        turn_id = timestamp_id("chatturn")

        # ---- INPUT GUARDRAILS (Security & Governance §1): PII redaction + prompt-injection/
        # jailbreak/oversize detection BEFORE any context assembly or LLM call. A BLOCK
        # short-circuits with a safe refusal; PII is redacted from the question before it reaches
        # the model. ----
        input_gr = self.guardrails.check_input(request.question) if self.guardrails else None
        guardrails_report: dict = {}
        if input_gr is not None:
            guardrails_report["input"] = input_gr.model_dump(mode="json")
            if input_gr.blocked:
                return self._blocked_response(request, conversation_id, turn_id, input_gr, guardrails_report)
        safe_question = input_gr.sanitized_text if input_gr else request.question

        # Assemble context from the SANITIZED question so redacted PII never enters retrieval/prompt.
        safe_request = request.model_copy(update={"question": safe_question})
        context_items = self.context_assembler.assemble(safe_request)

        # COMP-001 request-level guardrail: screen for prohibited performance claims.
        compliance_block = self._compliance_screen(safe_question)

        prompt_context = "\n\n".join(
            f"[{item.source.value}] {item.title}\n{item.content}"
            for item in context_items[:12]
        )

        prompt = f"""
Question:
{safe_question}

Persona:
{request.persona.value}

Scope:
{request.scope_type.value} {request.scope_id}

Context:
{prompt_context}

Instructions:
Answer with evidence. Include what data was used and what next action should be taken.
"""

        raw_answer = self.llm.generate(
            prompt,
            {"system_prompt": "You are iPerform Insights & Coaching AI Assistant. "
                              "Answer using only the provided context; cite concrete figures."},
        )

        # Mock adapter gives generic answer, so augment with deterministic evidence response.
        answer = self._grounded_answer(safe_request, context_items, raw_answer, compliance_block)

        # ---- OUTPUT GUARDRAILS (Security & Governance §3): PII filtering + toxicity/content-
        # safety + numeric-grounding/hallucination check on the final answer. PII is redacted; a
        # BLOCK replaces the answer with a safe notice; grounding/toxicity are surfaced. ----
        if self.guardrails is not None:
            output_gr = self.guardrails.check_output(answer, prompt_context)
            guardrails_report["output"] = output_gr.model_dump(mode="json")
            if output_gr.blocked:
                answer = ("⚠️ The generated response was withheld by the output guardrails "
                          f"({output_gr.summary()}). Please rephrase your question.")
            elif output_gr.redacted:
                answer = output_gr.sanitized_text

        reasoning_steps = [
            "Resolved persona and scope.",
            f"Applied input guardrails ({input_gr.summary() if input_gr else 'disabled'}).",
            "Screened the request against COMP-001 prohibited-claim rules.",
            "Retrieved context memory.",
            "Retrieved knowledge/RAG snippets where available.",
            "Retrieved/generated insight context.",
            "Retrieved predictions, opportunities and recommendations.",
            "Generated grounded assistant answer.",
            "Persisted conversation to memory when enabled.",
        ]
        if compliance_block:
            reasoning_steps.insert(2, f"COMP-001 BLOCK raised: prohibited claim {compliance_block['terms']}.")

        # Record a reasoning trace anchored to the advisor/scope so the NEXT question can
        # retrieve and build on it (reasoning-trace reuse). Evidence carries the real traversal
        # path + the prior traces reused — the same data the Explainability view renders.
        graph_item = next((i for i in context_items if i.source == ChatContextSource.GRAPH_REASONING), None)
        traversal_meta = (graph_item.metadata if graph_item else {}) or {}
        try:
            from app.ai.reasoning.graph_reasoner import GraphReasoner

            trace_steps = reasoning_steps + [
                f"Walked {len(traversal_meta.get('path', []))} graph hops for relational grounding.",
                f"Reused {len(traversal_meta.get('prior_reasoning_ids', []))} prior reasoning trace(s).",
                f"Conclusion: {answer.strip().splitlines()[0][:200] if answer.strip() else 'n/a'}",
            ]
            GraphReasoner().record_reasoning(
                request.scope_type.value, request.scope_id, trace_steps,
                evidence={"question": request.question,
                          "traversal_path": traversal_meta.get("path", []),
                          "prior_reasoning_ids": traversal_meta.get("prior_reasoning_ids", []),
                          "peer_success_patterns": (traversal_meta.get("traversal") or {}).get("peer_success_patterns", [])})
        except Exception:  # noqa: BLE001 — trace recording must never break the answer
            pass

        return ChatResponse(
            conversation_id=conversation_id,
            conversation_turn_id=turn_id,
            answer=answer,
            persona=request.persona,
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            context_items=context_items,
            reasoning_steps=reasoning_steps,
            confidence=(0.99 if compliance_block else (0.82 if context_items else 0.55)),
            guardrails=guardrails_report,
        )

    def _blocked_response(self, request, conversation_id, turn_id, input_gr, guardrails_report) -> ChatResponse:
        """Input guardrails BLOCKED the request (injection/jailbreak/oversize) — return a safe
        refusal without ever assembling context or calling the model."""
        return ChatResponse(
            conversation_id=conversation_id,
            conversation_turn_id=turn_id,
            answer=GuardrailService.safe_refusal(input_gr),
            persona=request.persona,
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            context_items=[],
            reasoning_steps=[
                "Resolved persona and scope.",
                f"Input guardrails BLOCKED the request: {input_gr.summary()}.",
                "Returned a safe refusal without calling the model.",
            ],
            confidence=0.99,
            guardrails=guardrails_report,
        )

    @staticmethod
    def _compliance_screen(question: str) -> dict | None:
        text = (question or "").lower()
        hits = [t for t in ComplianceAgent.PROHIBITED_CLAIMS if t in text]
        return {"rule": "COMP-001", "level": "BLOCK", "terms": hits} if hits else None

    def _grounded_answer(self, request: ChatRequest, items, raw_answer: str, compliance_block: dict | None = None) -> str:
        recs = [i for i in items if i.source.value == "Recommendations"]
        opps = [i for i in items if i.source.value == "Opportunities"]
        preds = [i for i in items if i.source.value == "Predictions"]
        insights = [i for i in items if i.source.value == "Insights"]
        memory = [i for i in items if i.source.value == "Context Memory"]

        lines: list[str] = []
        if compliance_block:
            term = compliance_block["terms"][0]
            lines.extend([
                f"⛔ Compliance block (COMP-001): this request references a prohibited performance "
                f'claim ("{term}"). I can\'t advise offering, marketing, or recommending a product on a '
                "guaranteed-return / risk-free / no-loss basis — that violates COMP-001 (prohibited "
                "performance claims) and firm supervisory policy.",
                "",
                "What you can do: present products with balanced, suitability-documented disclosures of "
                "risk and expected return, and route any performance representations through compliance "
                "review before client contact.",
                "",
            ])
        has_real_answer = bool(raw_answer) and "[mock-llm" not in raw_answer

        if has_real_answer:
            # Real LLM (Claude): its question-specific answer LEADS — never buried under
            # boilerplate. A compact grounding footer names the strongest evidence used
            # (the full instrumented item list rides along in context_items).
            lines.append(raw_answer.strip())
            grounding: list[str] = []
            if recs:
                grounding.append(f"Top-ranked recommendation: {recs[0].content}")
            if opps:
                grounding.append(f"Top opportunity: {opps[0].title} — {opps[0].content}")
            if preds:
                grounding.append(f"Prediction signal: {preds[0].title} — {preds[0].content}")
            if grounding:
                lines.extend(["", "---", "Grounding highlights:"] + [f"- {g}" for g in grounding])
            return "\n".join(lines)

        # Mock mode: no real prose exists, so the deterministic evidence composition IS the answer.
        lines.extend([
            f"For {request.scope_type.value} {request.scope_id}, here is the grounded answer:",
            "",
        ])
        if insights:
            lines.append(f"Insight summary: {insights[0].content}")
        if recs:
            lines.append(f"Top recommendation: {recs[0].content}")
        if opps:
            lines.append(f"Top opportunity: {opps[0].title} — {opps[0].content}")
        if preds:
            lines.append(f"Prediction signal: {preds[0].title} — {preds[0].content}")
        if memory and memory[0].content and "No relevant memories" not in memory[0].content:
            lines.append("Relevant memory was used to preserve prior context.")
        lines.extend([
            "",
            "Next action: review the evidence and, if the recommendation is accepted or completed, capture feedback so future ranking can improve.",
        ])
        return "\n".join(lines)
