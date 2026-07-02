from __future__ import annotations
from app.ai.adapters.model_adapter import ModelAdapter


class SmartSdkModelAdapter(ModelAdapter):
    def generate_text(self, prompt: str, *, system_prompt: str | None = None) -> str:
        raise NotImplementedError("SMARTSDK adapter will be implemented after framework handoff")

    def generate_json(self, prompt: str, *, system_prompt: str | None = None) -> dict:
        raise NotImplementedError("SMARTSDK adapter will be implemented after framework handoff")

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError("SMARTSDK adapter will be implemented after framework handoff")
