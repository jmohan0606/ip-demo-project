from app.agents.registry.agent_registry import AgentRegistry
from app.agents.state.agent_state import AgenticRequest, AgenticResponse, AgentWorkflowState
from app.agents.workflows.advisor_coaching_graph import AdvisorCoachingAgentGraph
from app.shared.ids import timestamp_id
class AgenticAiService:
    def __init__(self): self.graph=AdvisorCoachingAgentGraph(); self.registry=AgentRegistry()
    def run(self,request:AgenticRequest)->AgenticResponse:
        final=self.graph.run(AgentWorkflowState(request=request,run_id=timestamp_id('agentrun')))
        return AgenticResponse(run_id=final.run_id,answer=final.answer,final_agent=final.current_agent,tasks=final.tasks,evidence=final.evidence,reasoning_steps=final.reasoning_steps,recommendations=final.recommendations,opportunities=final.opportunities,predictions=final.predictions,confidence=final.confidence)
    def list_agents(self): return self.registry.list_agents()
