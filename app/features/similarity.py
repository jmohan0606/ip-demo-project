from __future__ import annotations

import math

from app.features.models import FeatureVector, SimilarityResult


class SimilarityService:
    def cosine(self, a: dict[str, float], b: dict[str, float]) -> float:
        keys = sorted(set(a) | set(b))
        av = [float(a.get(k, 0.0)) for k in keys]
        bv = [float(b.get(k, 0.0)) for k in keys]
        dot = sum(x * y for x, y in zip(av, bv))
        an = math.sqrt(sum(x * x for x in av)) or 1.0
        bn = math.sqrt(sum(y * y for y in bv)) or 1.0
        return dot / (an * bn)

    def top_similar(self, target: FeatureVector, candidates: list[FeatureVector], top_k: int = 5) -> list[SimilarityResult]:
        scored = []
        for candidate in candidates:
            if candidate.entity_type == target.entity_type and candidate.entity_id == target.entity_id:
                continue
            score = self.cosine(target.features, candidate.features)
            matched = sorted(set(target.features).intersection(candidate.features))[:6]
            scored.append(
                SimilarityResult(
                    entity_id=candidate.entity_id,
                    entity_name=candidate.metadata.get("name", candidate.entity_id),
                    similarity=round(score, 4),
                    explanation="Similar feature pattern across revenue, AUM, NNM, managed revenue mix and activity signals.",
                    features_matched=matched,
                )
            )
        scored.sort(key=lambda item: item.similarity, reverse=True)
        return scored[:top_k]
