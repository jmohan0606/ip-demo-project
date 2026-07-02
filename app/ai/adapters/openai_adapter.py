from __future__ import annotations
import json
from app.ai.adapters.model_adapter import ModelAdapter
from app.config.settings import get_settings


class OpenAIModelAdapter(ModelAdapter):
    def __init__(self) -> None:
        self.settings = get_settings()

    def _client(self):
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        from openai import OpenAI
        return OpenAI(api_key=self.settings.openai_api_key)

    def generate_text(self, prompt: str, *, system_prompt: str | None = None) -> str:
        client = self._client()
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def generate_json(self, prompt: str, *, system_prompt: str | None = None) -> dict:
        client = self._client()
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt or "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "{}")

    def embed_text(self, text: str) -> list[float]:
        client = self._client()
        response = client.embeddings.create(model=self.settings.openai_embedding_model, input=text)
        return response.data[0].embedding
