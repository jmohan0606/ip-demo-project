from app.agents.core.base_agent import BaseAgent
class ExplainabilityAgent(BaseAgent):
    name='explainability_agent'; description='Consolidates evidence and reasoning.'
    def run(self,state):
        task=self.create_task('Build explainability'); sources=sorted({e.source for e in state.evidence}); state.context['explainability']={'evidence_sources':sources,'evidence_count':len(state.evidence),'errors':state.errors}; state.reasoning_steps.append(f"Explainability Agent consolidated {len(state.evidence)} evidence items from {', '.join(sources) or 'no sources'}."); state.tasks.append(self.complete_task(task,state.context['explainability'])); return state
