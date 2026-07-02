from __future__ import annotations
from abc import ABC, abstractmethod


class ModelAdapter(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, *, system_prompt: str | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_json(self, prompt: str, *, system_prompt: str | None = None) -> dict:
        raise NotImplementedError

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError
