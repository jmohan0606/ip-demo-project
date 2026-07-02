from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.agents.tools.service_tools import AgentToolbox
class PredictionAgent(BaseAgent):
    name='prediction_agent'; description='Runs prediction tools.'
    def __init__(self): self.tools=AgentToolbox()
    def run(self,state):
        task=self.create_task('Run predictions')
        try:
            entity=state.request.scope_id if state.request.scope_type=='Advisor' else None; preds=self.tools.run_predictions(entity); state.predictions=preds
            for p in preds[:5]: state.evidence.append(AgentEvidence(source='Prediction Engine',title=p.get('prediction_type','Prediction'),content=p.get('explanation',''),score=p.get('score'),metadata=p))
            state.reasoning_steps.append('Prediction Agent generated signals.'); state.tasks.append(self.complete_task(task, {'predictions': len(preds)}))
        except Exception as e: state.errors.append(str(e)); state.tasks.append(self.fail_task(task,e))
        return state
