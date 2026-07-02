from __future__ import annotations

import hashlib
import math
from collections import Counter
import networkx as nx

from app.models.embeddings import EmbeddingEntityType, EmbeddingType, NodeEmbedding
from app.shared.ids import timestamp_id


class GraphEmbeddingEngine:
    """Local graph embedding approximation.

    This is not a heavy GNN. It creates deterministic demo-realistic graph embeddings
    using graph structure, degree, centrality, local neighborhood signatures and a
    stable hash projection. Later this can be swapped for real GraphSAGE/node2vec.
    """

    def __init__(self, dimension: int = 32) -> None:
        self.dimension = dimension

    def _hash_bucket(self, text: str) -> int:
        return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % self.dimension

    def _normalize(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [round(v / norm, 6) for v in vector]

    def embed_graph(self, graph: nx.Graph, entity_types: list[EmbeddingEntityType]) -> list[NodeEmbedding]:
        pagerank = nx.pagerank(graph, max_iter=50)
        embeddings: list[NodeEmbedding] = []
        allowed = {x.value for x in entity_types}

        for node, attrs in graph.nodes(data=True):
            entity_type = attrs.get("entity_type")
            entity_id = attrs.get("entity_id")
            if entity_type not in allowed or not entity_id:
                continue

            vector = [0.0] * self.dimension
            degree = graph.degree(node)
            vector[0] = degree
            vector[1] = pagerank.get(node, 0.0) * 1000

            neighbor_types = Counter(graph.nodes[n].get("entity_type", "Unknown") for n in graph.neighbors(node))
            for ntype, count in neighbor_types.items():
                vector[self._hash_bucket(f"type:{ntype}")] += count

            for key, value in attrs.items():
                vector[self._hash_bucket(f"attr:{key}:{value}")] += 1

            # include one-hop relation signatures
            for neighbor in graph.neighbors(node):
                edge_attrs = graph.get_edge_data(node, neighbor) or {}
                relation = edge_attrs.get("relation", "related")
                vector[self._hash_bucket(f"rel:{relation}")] += 1

            normalized = self._normalize(vector)
            embeddings.append(NodeEmbedding(
                embedding_id=timestamp_id("emb"),
                entity_type=EmbeddingEntityType(entity_type),
                entity_id=entity_id,
                embedding_type=EmbeddingType.GRAPH,
                model_name="networkx_local_graph_signature_v1",
                vector=normalized,
                vector_preview=",".join(str(x) for x in normalized[:8]),
            ))
        return embeddings
