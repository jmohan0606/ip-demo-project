from __future__ import annotations

from app.knowledge.chunking import TextChunker
from app.knowledge.document_parser import DocumentParser
from app.models.knowledge import KnowledgeSearchRequest
from app.services.knowledge_management_service import KnowledgeManagementService

def main() -> None:
    text = DocumentParser().parse("data/documents/sample_knowledge/managed_account_growth_playbook.txt")
    assert "Managed Account Growth Playbook" in text
    chunks = TextChunker(chunk_size=300, overlap=50).chunk_text("DOC_TEST", text)
    assert len(chunks) >= 1
    service = KnowledgeManagementService()
    results = service.ingest_sample_knowledge()
    assert len(results) >= 4
    search = service.search(KnowledgeSearchRequest(query="managed account recommendation evidence", top_k=3))
    assert len(search.results) >= 1
    print("Knowledge Management validation passed.")
    print(f"Sample documents ingested: {len(results)}")
    print(f"Search results: {len(search.results)}")

if __name__ == "__main__":
    main()
