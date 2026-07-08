from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.config.settings import get_settings
from app.knowledge.chunking import TextChunker
from app.knowledge.document_parser import DocumentParser
from app.knowledge.embedding_service import KnowledgeEmbeddingService
from app.knowledge.knowledge_catalog_repository import KnowledgeCatalogRepository
from app.knowledge.tigergraph_document_linker import TigerGraphDocumentLinker
from app.knowledge.vector_store import KnowledgeVectorStore
from app.models.knowledge import KnowledgeDocument, KnowledgeDocumentStatus, KnowledgeIngestionRequest, KnowledgeIngestionResult, KnowledgeSearchRequest, KnowledgeSearchResponse


class KnowledgeManagementService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.parser = DocumentParser()
        self.chunker = TextChunker()
        self.embedder = KnowledgeEmbeddingService()
        self.vector_store = KnowledgeVectorStore()
        self.catalog = KnowledgeCatalogRepository()
        self.linker = TigerGraphDocumentLinker()

    def ingest_document(self, request: KnowledgeIngestionRequest) -> KnowledgeIngestionResult:
        if not request.source_path:
            raise ValueError("source_path is required")
        source_path = Path(request.source_path)
        text = self.parser.parse(source_path)

        # Idempotency guard: the same file content under the same name must not index
        # twice (root cause of the corpus reaching 10 copies of every document —
        # repeated ingest-samples calls each minted a fresh DOC_<uuid>).
        import hashlib
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        existing = self.catalog.find_document(source_path.name, content_hash)
        if existing:
            return KnowledgeIngestionResult(
                document=existing, chunks=[], collection_name=request.collection_name,
                indexed_count=0, status=existing.status,
                message=f"Skipped duplicate: '{source_path.name}' already indexed as "
                        f"{existing.document_id} with identical content (sha256 match).",
            )

        document_id = f"DOC_{uuid4().hex[:12]}"
        document = KnowledgeDocument(
            document_id=document_id,
            document_name=source_path.name,
            document_type=request.document_type,
            document_category=request.document_category,
            source_path=str(source_path),
            status=KnowledgeDocumentStatus.PARSED,
        )
        chunks = self.chunker.chunk_text(document_id, text)
        for chunk in chunks:
            chunk.metadata.update({
                "document_name": document.document_name,
                "document_category": document.document_category,
                "collection_name": request.collection_name,
            })
        embeddings = self.embedder.embed_many([c.chunk_text for c in chunks]) if chunks else []
        indexed = self.vector_store.upsert_chunks(request.collection_name, chunks, embeddings, document.document_name, document.document_category)
        document.status = KnowledgeDocumentStatus.INDEXED
        self.catalog.save_document(document, {"collection_name": request.collection_name, "chunk_count": len(chunks), "indexed_count": indexed, "content_hash": content_hash})
        for chunk in chunks:
            self.catalog.save_chunk(chunk.chunk_id, chunk.document_id, chunk.chunk_index, chunk.chunk_summary, chunk.metadata)
        graph_link = self.linker.link_document(document, chunks)
        return KnowledgeIngestionResult(document=document, chunks=chunks, collection_name=request.collection_name, indexed_count=indexed, status=document.status, message=f"Document indexed and linked. {graph_link}")

    def dedupe_corpus(self) -> dict:
        """Remove duplicate documents (same document_name) from the catalog AND the
        vector index, keeping the earliest copy of each. One-time repair for the
        pre-idempotency corpus where every sample doc was ingested repeatedly."""
        import json as _json
        docs = self.catalog.list_documents()
        by_name: dict[str, list[dict]] = {}
        for row in docs:
            by_name.setdefault(row["document_name"], []).append(row)
        removed, kept = [], []
        for name, rows in by_name.items():
            rows.sort(key=lambda r: r.get("uploaded_at") or "")
            kept.append(rows[0]["document_id"])
            for dup in rows[1:]:
                meta = _json.loads(dup.get("metadata_json") or "{}")
                collection = meta.get("collection_name") or "iperform_knowledge_base"
                self.vector_store.delete_document_chunks(collection, dup["document_id"])
                self.catalog.delete_document(dup["document_id"])
                removed.append({"document_id": dup["document_id"], "document_name": name})
        return {"documents_before": len(docs), "documents_kept": len(kept),
                "duplicates_removed": len(removed), "removed": removed}

    def ingest_sample_knowledge(self) -> list[KnowledgeIngestionResult]:
        sample_dir = Path(self.settings.documents_path) / "sample_knowledge"
        if not sample_dir.exists():
            sample_dir = Path("data/documents/sample_knowledge")
        # Ingest every supported format, not just .txt (CLAUDE.md 9.8) — exercises the
        # real PDF/DOCX/PPTX parsers, not only the text path.
        supported = {".txt", ".md", ".pdf", ".docx", ".pptx"}
        results = []
        for file_path in sorted(p for p in sample_dir.iterdir() if p.suffix.lower() in supported):
            category = self._category_for(file_path.name)
            results.append(self.ingest_document(KnowledgeIngestionRequest(source_path=str(file_path), document_category=category)))
        return results

    @staticmethod
    def _category_for(file_name: str) -> str:
        name = file_name.lower()
        if "compliance" in name or "policy" in name or "procedure" in name:
            return "Compliance"
        if "agp" in name:
            return "AGP Guide"
        if "glossary" in name:
            return "Glossary"
        if "playbook" in name:
            return "Playbook"
        if "market" in name or "research" in name:
            return "Research"
        if "crm" in name or "engagement" in name:
            return "CRM Engagement"
        return "Practice Guideline"

    def search(self, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        embedding = self.embedder.embed(request.query)
        results = self.vector_store.search(request.collection_name, embedding, request.query, request.top_k)
        if request.document_category:
            results = [r for r in results if r.metadata.get("document_category") == request.document_category]
        return KnowledgeSearchResponse(query=request.query, results=results)

    def list_documents(self) -> list[dict]:
        return self.catalog.list_documents()


# Runtime validation fallback helper.
def _preloaded_knowledge_fallback_search(query: str, top_k: int = 5) -> list[dict]:
    import json
    from pathlib import Path
    index = Path("data/chroma/preloaded_knowledge_index.json")
    if not index.exists():
        return []
    terms = {x.lower() for x in query.split() if len(x) > 2}
    rows = json.loads(index.read_text(encoding="utf-8"))
    scored = []
    for row in rows:
        text = row.get("text", "")
        score = sum(1 for t in terms if t in text.lower())
        scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "document_name": r["document_name"],
            "chunk_text": r["text"],
            "score": float(score),
            "metadata": {"source": "preloaded_chroma_fallback", "chunk_id": r["id"]},
        }
        for score, r in scored[:top_k]
        if score >= 0
    ]
