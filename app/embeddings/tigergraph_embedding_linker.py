from __future__ import annotations

from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient
from app.models.embeddings import NodeEmbedding, SimilarityMatch


class TigerGraphEmbeddingLinker:
    def __init__(self) -> None:
        self.upsert = TigerGraphUpsertClient()

    def upsert_embedding(self, emb: NodeEmbedding) -> dict:
        payload = {
            "embedding_id": emb.embedding_id,
            "entity_type": emb.entity_type.value,
            "entity_id": emb.entity_id,
            "embedding_type": emb.embedding_type.value,
            "model_name": emb.model_name,
            "vector_preview": emb.vector_preview,
            "created_ts": emb.created_ts.isoformat(),
            "status": emb.status,
        }
        result = self.upsert.upsert_vertex("phx_dm_embedding", emb.embedding_id, payload)
        edge_map = {
            "Advisor": "phx_dm_embedding_for_advisor",
            "Household": "phx_dm_embedding_for_household",
            "Product": "phx_dm_embedding_for_product",
        }
        edge_type = edge_map.get(emb.entity_type.value)
        if edge_type:
            self.upsert.upsert_edge(edge_type, emb.embedding_id, emb.entity_id, {})
        return result

    def upsert_similarity(self, match: SimilarityMatch) -> dict:
        payload = {
            "similarity_id": match.similarity_id,
            "source_entity_type": match.source_entity_type.value,
            "source_entity_id": match.source_entity_id,
            "target_entity_type": match.target_entity_type.value,
            "target_entity_id": match.target_entity_id,
            "similarity_type": match.similarity_type.value,
            "similarity_score": match.similarity_score,
            "explanation": match.explanation,
            "created_ts": match.created_ts.isoformat(),
        }
        result = self.upsert.upsert_vertex("phx_dm_similarity_match", match.similarity_id, payload)
        if match.source_entity_type.value == "Advisor":
            self.upsert.upsert_edge("phx_dm_similarity_source_advisor", match.similarity_id, match.source_entity_id, {})
            self.upsert.upsert_edge("phx_dm_similarity_target_advisor", match.similarity_id, match.target_entity_id, {})
        if match.source_entity_type.value == "Household":
            self.upsert.upsert_edge("phx_dm_similarity_source_household", match.similarity_id, match.source_entity_id, {})
            self.upsert.upsert_edge("phx_dm_similarity_target_household", match.similarity_id, match.target_entity_id, {})
        return result
