from __future__ import annotations

import math
from app.models.embeddings import EmbeddingEntityType, SimilarityMatch, SimilarityType, NodeEmbedding
from app.shared.ids import timestamp_id


class SimilarityEngine:
    @staticmethod
    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)

    def build_similarity_matches(self, embeddings: list[NodeEmbedding], top_k: int = 5) -> list[SimilarityMatch]:
        matches: list[SimilarityMatch] = []
        by_type: dict[EmbeddingEntityType, list[NodeEmbedding]] = {}
        for emb in embeddings:
            by_type.setdefault(emb.entity_type, []).append(emb)

        for entity_type, items in by_type.items():
            if entity_type not in {EmbeddingEntityType.ADVISOR, EmbeddingEntityType.HOUSEHOLD}:
                continue

            sim_type = SimilarityType.ADVISOR_PEER if entity_type == EmbeddingEntityType.ADVISOR else SimilarityType.HOUSEHOLD_OPPORTUNITY

            for source in items:
                scored = []
                for target in items:
                    if target.entity_id == source.entity_id:
                        continue
                    score = self.cosine(source.vector, target.vector)
                    scored.append((target, score))
                scored.sort(key=lambda x: x[1], reverse=True)
                for target, score in scored[:top_k]:
                    matches.append(SimilarityMatch(
                        similarity_id=timestamp_id("sim"),
                        source_entity_type=entity_type,
                        source_entity_id=source.entity_id,
                        target_entity_type=entity_type,
                        target_entity_id=target.entity_id,
                        similarity_type=sim_type,
                        similarity_score=round(float(score), 6),
                        explanation="Similar graph neighborhood, relationship pattern, and local structural signature.",
                    ))
        return matches
