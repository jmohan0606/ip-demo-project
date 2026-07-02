from __future__ import annotations

import streamlit as st

from app.models.embeddings import EmbeddingBuildRequest, EmbeddingEntityType, SimilaritySearchRequest
from app.services.embedding_similarity_service import EmbeddingSimilarityService


def render_embedding_similarity_page() -> None:
    st.title("Graph Embeddings & Similarity")
    st.caption("Build local graph embeddings and peer/household similarity using NetworkX graph structure.")

    service = EmbeddingSimilarityService()
    tab_build, tab_search, tab_embeddings, tab_matches = st.tabs(["Build", "Similarity Search", "Embeddings", "Matches"])

    with tab_build:
        selected = st.multiselect("Entity Types", [e.value for e in EmbeddingEntityType], default=["Advisor", "Household"])
        top_k = st.slider("Top K Similarity", 1, 10, 5)
        write = st.checkbox("Write to TigerGraph", value=False)
        if st.button("Build Embeddings & Similarity"):
            with st.status("Building graph and embeddings...", expanded=True) as status:
                result = service.build_embeddings_and_similarity(
                    EmbeddingBuildRequest(
                        entity_types=[EmbeddingEntityType(x) for x in selected],
                        top_k_similarity=top_k,
                        write_to_tigergraph=write,
                    )
                )
                st.json(result.model_dump())
                status.update(label="Embedding build complete", state="complete")

    with tab_search:
        entity_type = st.selectbox("Entity Type", ["Advisor", "Household"])
        entity_id = st.text_input("Entity ID", value="ADV0001" if entity_type == "Advisor" else "HH00001")
        top_k_s = st.slider("Top K", 1, 20, 10)
        if st.button("Find Similar Entities"):
            rows = service.search_similarity(SimilaritySearchRequest(
                entity_type=EmbeddingEntityType(entity_type),
                entity_id=entity_id,
                top_k=top_k_s,
            ))
            st.dataframe(rows, use_container_width=True)

    with tab_embeddings:
        st.dataframe(service.list_embeddings(limit=200), use_container_width=True)

    with tab_matches:
        st.dataframe(service.list_similarity(limit=200), use_container_width=True)
