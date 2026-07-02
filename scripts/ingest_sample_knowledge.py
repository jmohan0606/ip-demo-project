from __future__ import annotations
from app.services.knowledge_management_service import KnowledgeManagementService

def main() -> None:
    results = KnowledgeManagementService().ingest_sample_knowledge()
    print(f"Ingested {len(results)} sample documents.")
    for result in results:
        print(f"- {result.document.document_name}: {result.indexed_count} chunks")

if __name__ == "__main__":
    main()
