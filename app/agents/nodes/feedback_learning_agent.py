from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.services.feedback_learning_service import FeedbackLearningService
class FeedbackLearningAgent(BaseAgent):
    name='feedback_learning_agent'; description='Retrieves feedback learning signals.'
    def run(self,state):
        task=self.create_task('Retrieve learning signals')
        try:
            signals=FeedbackLearningService().list_learning_signals(limit=20); state.feedback_signals=signals
            for s in signals[:5]: state.evidence.append(AgentEvidence(source='Feedback Learning',title=s.get('signal_type','Learning Signal'),content=s.get('signal_summary',''),score=s.get('signal_value'),metadata=s))
            state.reasoning_steps.append('Feedback Learning Agent retrieved learning signals.'); state.tasks.append(self.complete_task(task, {'learning_signals': len(signals)}))
        except Exception as e: state.errors.append(str(e)); state.tasks.append(self.fail_task(task,e))
        return state
