from __future__ import annotations

import hashlib
import math


class DeterministicEmbeddingProvider:
    """Local deterministic embedding fallback.

    This keeps the app runnable without OpenAI/Azure credentials. It is not a
    semantic embedding model, but it provides stable vectors for demo/runtime tests.
    """

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        for i in range(self.dimensions):
            b = digest[i % len(digest)]
            values.append((b / 255.0) * 2 - 1)
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]
