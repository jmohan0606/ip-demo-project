from __future__ import annotations
import streamlit as st
from app.models.memory import ContextMemoryCreateRequest, MemoryRetrievalRequest, MemoryScopeType, MemoryType
from app.services.context_service import ContextService
from app.services.memory_service import MemoryService

def render_memory_timeline_page() -> None:
    st.title("Context Graph & Temporal Memory")
    st.caption("Retrieve, create, and inspect time-versioned organizational memory.")
    service = MemoryService()
    context_service = ContextService()
    tab_create, tab_retrieve, tab_counts = st.tabs(["Create Memory", "Retrieve Context", "Memory Counts"])

    with tab_create:
        scope_type = st.selectbox("Scope Type", [x.value for x in MemoryScopeType], index=4)
        scope_id = st.text_input("Scope ID", value="ADV0001")
        memory_type = st.selectbox("Memory Type", [x.value for x in MemoryType], index=4)
        title = st.text_input("Title", value="Advisor coaching memory")
        summary = st.text_area("Summary", value="Advisor has a managed revenue opportunity and needs follow-up coaching.")
        confidence = st.slider("Confidence", 0.0, 1.0, 0.85)
        if st.button("Create Memory"):
            memory = service.create_memory(
                ContextMemoryCreateRequest(
                    memory_type=MemoryType(memory_type),
                    scope_type=MemoryScopeType(scope_type),
                    scope_id=scope_id,
                    title=title,
                    summary=summary,
                    confidence=confidence,
                    facts={"created_from_ui": True},
                )
            )
            st.success("Memory created")
            st.json(memory.model_dump())

    with tab_retrieve:
        scope_type_r = st.selectbox("Retrieve Scope Type", [x.value for x in MemoryScopeType], index=4)
        scope_id_r = st.text_input("Retrieve Scope ID", value="ADV0001")
        query = st.text_input("Context Query", value="What coaching context should be used?")
        if st.button("Build Context Package"):
            package = context_service.build_context_package(
                MemoryRetrievalRequest(scope_type=MemoryScopeType(scope_type_r), scope_id=scope_id_r, query=query, limit=10)
            )
            st.metric("Evidence Count", package.evidence_count)
            st.text_area("Context Summary", value=package.context_summary, height=240)
            st.json([m.model_dump() for m in package.memories])

    with tab_counts:
        st.dataframe(service.memory_counts_by_type(), use_container_width=True)
