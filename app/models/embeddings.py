from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class EmbeddingEntityType(StrEnum):
    ADVISOR = "Advisor"
    HOUSEHOLD = "Household"
    PRODUCT = "Product"
    ACCOUNT = "Account"


class EmbeddingType(StrEnum):
    GRAPH = "graph_embedding"
    FEATURE = "feature_embedding"
    HYBRID = "hybrid_embedding"


class SimilarityType(StrEnum):
    ADVISOR_PEER = "Advisor Peer Similarity"
    HOUSEHOLD_OPPORTUNITY = "Household Opportunity Similarity"
    PRODUCT_AFFINITY = "Product Affinity Similarity"


class NodeEmbedding(BaseModel):
    embedding_id: str
    entity_type: EmbeddingEntityType
    entity_id: str
    embedding_type: EmbeddingType = EmbeddingType.GRAPH
    model_name: str = "networkx_local_graph_embedding"
    vector: list[float]
    vector_preview: str
    created_ts: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Active"


class SimilarityMatch(BaseModel):
    similarity_id: str
    source_entity_type: EmbeddingEntityType
    source_entity_id: str
    target_entity_type: EmbeddingEntityType
    target_entity_id: str
    similarity_type: SimilarityType
    similarity_score: float
    explanation: str
    created_ts: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingBuildRequest(BaseModel):
    entity_types: list[EmbeddingEntityType] = Field(default_factory=lambda: [EmbeddingEntityType.ADVISOR, EmbeddingEntityType.HOUSEHOLD])
    top_k_similarity: int = 5
    write_to_tigergraph: bool = True


class EmbeddingBuildResult(BaseModel):
    embeddings_created: int
    similarity_matches_created: int
    status: str
    message: str


class SimilaritySearchRequest(BaseModel):
    entity_type: EmbeddingEntityType
    entity_id: str
    top_k: int = 10
