from __future__ import annotations

from app.models.embeddings import EmbeddingBuildRequest, EmbeddingEntityType
from app.services.embedding_similarity_service import EmbeddingSimilarityService


def main() -> None:
    result = EmbeddingSimilarityService().build_embeddings_and_similarity(
        EmbeddingBuildRequest(
            entity_types=[EmbeddingEntityType.ADVISOR, EmbeddingEntityType.HOUSEHOLD],
            top_k_similarity=5,
            write_to_tigergraph=False,
        )
    )
    print("Embedding and similarity build completed.")
    print(result.model_dump())


if __name__ == "__main__":
    main()
