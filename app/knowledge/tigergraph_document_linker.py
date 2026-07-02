from __future__ import annotations

from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument


class TigerGraphDocumentLinker:
    def __init__(self) -> None:
        self.upsert = TigerGraphUpsertClient()

    def link_document(self, document: KnowledgeDocument, chunks: list[KnowledgeChunk]) -> dict:
        doc_payload = document.model_dump()
        doc_payload["document_type"] = document.document_type.value
        doc_payload["status"] = document.status.value
        self.upsert.upsert_vertex("phx_dm_document", document.document_id, doc_payload)
        linked = 0
        for chunk in chunks:
            payload = {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "chunk_summary": chunk.chunk_summary or "",
                "chroma_collection": chunk.metadata.get("collection_name", "iperform_knowledge_base"),
                "status": "Active",
            }
            self.upsert.upsert_vertex("phx_dm_document_chunk", chunk.chunk_id, payload)
            self.upsert.upsert_edge("phx_dm_document_has_chunk", document.document_id, chunk.chunk_id, {})
            linked += 1
        return {"document_linked": True, "chunks_linked": linked}
