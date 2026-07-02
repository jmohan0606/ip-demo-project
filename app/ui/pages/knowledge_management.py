from __future__ import annotations

import streamlit as st
from app.models.knowledge import KnowledgeIngestionRequest, KnowledgeSearchRequest
from app.services.knowledge_management_service import KnowledgeManagementService


def render_knowledge_management_page() -> None:
    st.title("Knowledge Management & RAG")
    st.caption("Ingest practice guidelines, compliance policies, playbooks, AGP guides and glossary content into Chroma and TigerGraph.")

    service = KnowledgeManagementService()
    tab_ingest, tab_search, tab_library = st.tabs(["Ingest", "Search", "Library"])

    with tab_ingest:
        st.subheader("Sample Knowledge Ingestion")
        if st.button("Ingest Sample Knowledge"):
            with st.status("Ingesting sample knowledge...", expanded=True) as status:
                results = service.ingest_sample_knowledge()
                st.write(f"Documents indexed: {len(results)}")
                for result in results:
                    st.write({"document": result.document.document_name, "chunks": len(result.chunks), "indexed": result.indexed_count, "status": result.status})
                status.update(label="Knowledge ingestion complete", state="complete")

        st.subheader("Single Document Ingestion")
        source_path = st.text_input("Source path", value="data/documents/sample_knowledge/managed_account_growth_playbook.txt")
        category = st.selectbox("Category", ["Practice Guideline", "Compliance", "Playbook", "AGP Guide", "Glossary", "Research", "Other"])
        if st.button("Ingest Document"):
            result = service.ingest_document(KnowledgeIngestionRequest(source_path=source_path, document_category=category))
            st.success(result.message)
            st.json(result.document.model_dump())

    with tab_search:
        st.subheader("Knowledge Search")
        query = st.text_input("Question", value="What evidence is required for a managed account recommendation?")
        top_k = st.slider("Top K", min_value=1, max_value=10, value=5)
        if st.button("Search Knowledge"):
            response = service.search(KnowledgeSearchRequest(query=query, top_k=top_k))
            for result in response.results:
                with st.expander(f"{result.document_name} — {result.chunk_id}"):
                    st.write(result.chunk_text)
                    st.json(result.metadata)

    with tab_library:
        st.subheader("Document Library")
        st.dataframe(service.list_documents(), use_container_width=True)
