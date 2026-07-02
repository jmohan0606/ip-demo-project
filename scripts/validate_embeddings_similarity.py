from __future__ import annotations

from app.models.embeddings import EmbeddingBuildRequest, EmbeddingEntityType, SimilaritySearchRequest
from app.services.embedding_similarity_service import EmbeddingSimilarityService


def main() -> None:
    service = EmbeddingSimilarityService()
    result = service.build_embeddings_and_similarity(
        EmbeddingBuildRequest(
            entity_types=[EmbeddingEntityType.ADVISOR, EmbeddingEntityType.HOUSEHOLD],
            top_k_similarity=3,
            write_to_tigergraph=False,
        )
    )
    assert result.embeddings_created > 0
    assert result.similarity_matches_created > 0
    rows = service.search_similarity(
        SimilaritySearchRequest(entity_type=EmbeddingEntityType.ADVISOR, entity_id="ADV0001", top_k=3)
    )
    assert len(rows) >= 1
    print("Graph Embeddings & Similarity validation passed.")
    print(result.model_dump())
    print(f"Sample matches: {len(rows)}")


if __name__ == "__main__":
    main()
