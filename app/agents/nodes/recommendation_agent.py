from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.agents.tools.service_tools import AgentToolbox
class RecommendationAgent(BaseAgent):
    name='recommendation_agent'; description='Generates recommendation actions.'
    def __init__(self): self.tools=AgentToolbox()
    def run(self,state):
        task=self.create_task('Run recommendations')
        try:
            entity=state.request.scope_id if state.request.scope_type=='Advisor' else None; recs=self.tools.run_recommendations(entity); state.recommendations=recs
            for r in recs[:5]: state.evidence.append(AgentEvidence(source='Recommendation Engine',title=r.get('title','Recommendation'),content=r.get('action_text',''),score=r.get('score'),metadata=r))
            state.reasoning_steps.append('Recommendation Agent generated playbook-supported actions.'); state.tasks.append(self.complete_task(task, {'recommendations': len(recs)}))
        except Exception as e: state.errors.append(str(e)); state.tasks.append(self.fail_task(task,e))
        return state
