from __future__ import annotations

from app.embeddings.embedding_engine import GraphEmbeddingEngine
from app.embeddings.embedding_repository import EmbeddingRepository
from app.embeddings.graph_builder import DemoGraphBuilder
from app.embeddings.similarity_engine import SimilarityEngine
from app.embeddings.tigergraph_embedding_linker import TigerGraphEmbeddingLinker
from app.models.embeddings import EmbeddingBuildRequest, EmbeddingBuildResult, SimilaritySearchRequest


class EmbeddingSimilarityService:
    def __init__(self) -> None:
        self.repo = EmbeddingRepository()
        self.graph_builder = DemoGraphBuilder()
        self.embedding_engine = GraphEmbeddingEngine()
        self.similarity_engine = SimilarityEngine()
        self.linker = TigerGraphEmbeddingLinker()

    def build_embeddings_and_similarity(self, request: EmbeddingBuildRequest) -> EmbeddingBuildResult:
        graph = self.graph_builder.build_graph()
        embeddings = self.embedding_engine.embed_graph(graph, request.entity_types)
        matches = self.similarity_engine.build_similarity_matches(embeddings, request.top_k_similarity)

        for emb in embeddings:
            self.repo.save_embedding(emb)
            if request.write_to_tigergraph:
                self.linker.upsert_embedding(emb)

        for match in matches:
            self.repo.save_similarity(match)
            if request.write_to_tigergraph:
                self.linker.upsert_similarity(match)

        return EmbeddingBuildResult(
            embeddings_created=len(embeddings),
            similarity_matches_created=len(matches),
            status="completed",
            message="Graph embeddings and similarity matches generated.",
        )

    def search_similarity(self, request: SimilaritySearchRequest) -> list[dict]:
        return self.repo.list_similarity(request.entity_type.value, request.entity_id, request.top_k)

    def list_embeddings(self, entity_type: str | None = None, limit: int = 100) -> list[dict]:
        return self.repo.list_embeddings(entity_type, limit)

    def list_similarity(self, limit: int = 100) -> list[dict]:
        return self.repo.list_similarity(limit=limit)

    def counts(self) -> list[dict]:
        return self.repo.counts()
