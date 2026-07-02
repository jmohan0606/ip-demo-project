from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.agents.tools.service_tools import AgentToolbox
class ContextRetrievalAgent(BaseAgent):
    name='context_retrieval_agent'; description='Retrieves temporal memory context.'
    def __init__(self): self.tools=AgentToolbox()
    def run(self,state):
        task=self.create_task('Retrieve memory context')
        try:
            pkg=self.tools.retrieve_context(state.request.scope_type,state.request.scope_id,state.request.question); state.context['memory']=pkg; state.evidence.append(AgentEvidence(source='Context Memory',title='Context package',content=pkg.get('context_summary',''),score=pkg.get('evidence_count'),metadata=pkg)); state.reasoning_steps.append('Context Retrieval Agent retrieved temporal memory.'); state.tasks.append(self.complete_task(task, {'evidence_count': pkg.get('evidence_count',0)}))
        except Exception as e: state.errors.append(str(e)); state.tasks.append(self.fail_task(task,e))
        return state
