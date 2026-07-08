from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.agents.tools.service_tools import AgentToolbox
class OpportunityAgent(BaseAgent):
    name='opportunity_agent'; description='Detects and ranks opportunities.'
    def __init__(self): self.tools=AgentToolbox()
    def run(self,state):
        task=self.create_task('Run opportunities')
        try:
            entity=state.request.scope_id if state.request.scope_type=='Advisor' else None; opps=self.tools.run_opportunities(entity); state.opportunities=opps
            # Detection pipeline emits opportunity_type/impact_summary (not title/description).
            for o in opps[:5]: state.evidence.append(AgentEvidence(source='Opportunity Engine',title=o.get('opportunity_type') or o.get('title') or 'Opportunity',content=o.get('impact_summary') or o.get('description') or '',score=o.get('score'),metadata=o))
            top=', '.join(f"{o.get('opportunity_type')} ({o.get('severity')}, score {o.get('score')})" for o in opps[:3])
            state.reasoning_steps.append(f'Opportunity Agent ranked {len(opps)} opportunities'+(f': {top}' if top else '')+'.'); state.tasks.append(self.complete_task(task, {'opportunities': len(opps)}))
        except Exception as e: state.errors.append(str(e)); state.tasks.append(self.fail_task(task,e))
        return state
