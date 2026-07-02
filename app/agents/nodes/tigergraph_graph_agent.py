from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.agents.tools.service_tools import AgentToolbox
class TigerGraphGraphAgent(BaseAgent):
    name='tigergraph_graph_agent'; description='Queries TigerGraph through MCP-first graph access.'
    def __init__(self): self.tools=AgentToolbox()
    def run(self,state):
        task=self.create_task('Query graph evidence')
        try:
            health=self.tools.graph_health(); data={}
            if state.request.scope_type=='Advisor': data=self.tools.graph_query_advisor_evidence(state.request.scope_id)
            state.context['graph_health']=health; state.context['graph_evidence']=data; state.evidence.append(AgentEvidence(source='TigerGraph Graph Access',title=f"Graph mode: {health.get('active_mode')}",content='Graph evidence retrieved through MCP-first access.',metadata={'health':health,'data':data})); state.reasoning_steps.append('TigerGraph Graph Agent used MCP-first access with REST/mock fallback.'); state.tasks.append(self.complete_task(task, {'active_mode': health.get('active_mode')}))
        except Exception as e: state.errors.append(str(e)); state.tasks.append(self.fail_task(task,e))
        return state
