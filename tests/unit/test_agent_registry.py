from app.services.agentic_ai_service import AgenticAiService

def test_agent_registry_has_expected_agents():
    names={a['name'] for a in AgenticAiService().list_agents()}
    assert 'supervisor' in names
    assert 'context_retrieval_agent' in names
    assert 'tigergraph_graph_agent' in names
    assert 'ai_assistant_agent' in names
