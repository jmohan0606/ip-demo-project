from __future__ import annotations

import streamlit as st

from app.services.graph_access_service import GraphAccessService


def render_graph_access_status_page() -> None:
    st.title("TigerGraph MCP-First Graph Access")
    st.caption("Primary: existing TigerGraph MCP server. Fallback: TigerGraph REST. Final fallback: local mock graph service.")

    service = GraphAccessService()

    if st.button("Check Active Graph Access Mode"):
        with st.status("Checking MCP, REST and mock graph access...", expanded=True) as status:
            health = service.health()
            st.metric("Active Mode", health["active_mode"])
            st.json(health)
            status.update(label="Graph access check complete", state="complete")

    tab_query, tab_upsert, tab_schema, tab_mcp = st.tabs(["Query", "Upsert", "Schema", "MCP Tools"])

    with tab_query:
        st.subheader("Run Installed Query")
        query_name = st.text_input("Query Name", value="phx_dm_getInsightEvidenceForAdvisor")
        advisor_id = st.text_input("Advisor ID", value="ADV0001")
        if st.button("Run Query"):
            result = service.run_installed_query(query_name, {"advisorId": advisor_id, "advisor_id": advisor_id})
            st.json(result)

    with tab_upsert:
        st.subheader("Test Vertex Upsert")
        vertex_type = st.text_input("Vertex Type", value="phx_dm_context_memory")
        primary_key = st.text_input("Primary Key", value="MEM_UI_TEST")
        if st.button("Upsert Test Vertex"):
            result = service.upsert_vertex(
                vertex_type,
                primary_key,
                {
                    "memory_id": primary_key,
                    "memory_type": "Advisor Memory",
                    "scope_type": "Advisor",
                    "scope_id": "ADV0001",
                    "summary": "UI graph access test memory.",
                    "status": "Active",
                },
            )
            st.json(result)

    with tab_schema:
        if st.button("Get Schema"):
            st.json(service.schema())


    with tab_mcp:
        st.subheader("MCP Tool Discovery")
        st.caption("Uses the MCP SDK/library client to list tools from the existing TigerGraph MCP server.")
        if st.button("List MCP Tools"):
            try:
                st.json(service.list_mcp_tools())
            except Exception as exc:
                st.error(str(exc))
