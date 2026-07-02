from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.config import get_runtime_config
from app.graph import get_graph_runtime
from app.knowledge.chroma_adapter import ChromaAdapter
from app.knowledge.chunker import DocumentChunker
from app.knowledge.mock_vector_store import MockPersistentVectorStore
from app.knowledge.models import KnowledgeRuntimeResult


class KnowledgeRuntime:
    def __init__(self) -> None:
        self.config = get_runtime_config()
        self.chunker = DocumentChunker()
        self.chroma = ChromaAdapter(self.config.chroma_persist_dir, self.config.chroma_collection_name)
        self.mock = MockPersistentVectorStore(self.config.chroma_persist_dir, self.config.chroma_collection_name)
        self.graph = get_graph_runtime()

    def status(self) -> KnowledgeRuntimeResult:
        mode = "chroma" if self.chroma.is_available() else "mock_vector_store"
        count = self.chroma.count() if self.chroma.is_available() else self.mock.count()
        return KnowledgeRuntimeResult(
            status="success",
            mode=mode,
            operation="status",
            data={
                "collection_name": self.config.chroma_collection_name,
                "persist_dir": self.config.chroma_persist_dir,
                "chroma_available": self.chroma.is_available(),
                "active_mode": mode,
                "document_chunk_count": count,
            },
            fallback_used=mode != "chroma",
            message=f"Knowledge runtime active in {mode}",
        )

    def ingest_document(
        self,
        document_name: str,
        content: str,
        document_type: str = "playbook",
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeRuntimeResult:
        document_id = f"DOC-{uuid4().hex[:10].upper()}"
        metadata = metadata or {}
        metadata.update({"document_type": document_type})
        chunks = self.chunker.chunk(document_id, document_name, content, metadata)

        trace = []
        try:
            if self.chroma.is_available():
                upsert_result = self.chroma.upsert_chunks(chunks)
                mode = "chroma"
            else:
                raise RuntimeError(self.chroma.error or "Chroma unavailable")
        except Exception as exc:
            trace.append({"mode": "chroma", "status": "fallback", "message": str(exc)})
            upsert_result = self.mock.upsert_chunks(chunks)
            mode = "mock_vector_store"

        # Persist lineage to graph runtime. This will use MCP -> REST -> mock.
        doc_vertex = self.graph.upsert_vertex("Document", document_id, {
            "document_id": document_id,
            "document_name": document_name,
            "document_type": document_type,
            "chunk_count": len(chunks),
        })
        for chunk in chunks[:10]:
            self.graph.upsert_vertex("DocumentChunk", chunk.chunk_id, {
                "chunk_id": chunk.chunk_id,
                "document_id": document_id,
                "document_name": document_name,
                "chunk_index": chunk.chunk_index,
            })
            self.graph.upsert_edge("HAS_CHUNK", "Document", document_id, "DocumentChunk", chunk.chunk_id, {})

        return KnowledgeRuntimeResult(
            status="success",
            mode=mode,
            operation="ingest_document",
            data={
                "document_id": document_id,
                "document_name": document_name,
                "document_type": document_type,
                "chunks_created": len(chunks),
                "index_result": upsert_result,
                "graph_lineage": doc_vertex.to_dict(),
            },
            fallback_used=mode != "chroma" or doc_vertex.fallback_used,
            message=f"Document ingested into {mode} with graph lineage",
            trace=trace + doc_vertex.tool_trace,
        )

    def search(self, query: str, top_k: int = 5) -> KnowledgeRuntimeResult:
        trace = []
        try:
            if self.chroma.is_available():
                results = self.chroma.search(query, top_k)
                mode = "chroma"
            else:
                raise RuntimeError(self.chroma.error or "Chroma unavailable")
        except Exception as exc:
            trace.append({"mode": "chroma", "status": "fallback", "message": str(exc)})
            results = self.mock.search(query, top_k)
            mode = "mock_vector_store"

        return KnowledgeRuntimeResult(
            status="success",
            mode=mode,
            operation="search",
            data={
                "query": query,
                "collection": self.config.chroma_collection_name,
                "results": [result.__dict__ for result in results],
            },
            fallback_used=mode != "chroma",
            message=f"Knowledge search completed using {mode}",
            trace=trace,
        )


_knowledge_runtime: KnowledgeRuntime | None = None


def get_knowledge_runtime() -> KnowledgeRuntime:
    global _knowledge_runtime
    if _knowledge_runtime is None:
        _knowledge_runtime = KnowledgeRuntime()
    return _knowledge_runtime
