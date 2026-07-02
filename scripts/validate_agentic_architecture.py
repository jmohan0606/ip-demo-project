from app.agents.state.agent_state import AgenticRequest
from app.services.agentic_ai_service import AgenticAiService

def main():
    service=AgenticAiService(); agents=service.list_agents(); assert len(agents)>=10; names={a['name'] for a in agents}; assert 'supervisor' in names and 'recommendation_agent' in names and 'ai_assistant_agent' in names
    response=service.run(AgenticRequest(question='Why is my revenue low and what should I do next?',persona='Advisor',scope_type='Advisor',scope_id='ADV0001',requested_capabilities=['prediction','opportunity','recommendation'],write_to_tigergraph=False))
    assert response.answer and response.tasks and response.evidence
    print('True Agentic Architecture validation passed.'); print(f'Agents: {len(agents)}'); print(f'Tasks: {len(response.tasks)}'); print(f'Evidence: {len(response.evidence)}'); print(response.answer[:800])
if __name__=='__main__': main()
