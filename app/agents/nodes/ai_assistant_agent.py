from app.agents.core.base_agent import BaseAgent
class AiAssistantAgent(BaseAgent):
    name='ai_assistant_agent'; description='Synthesizes final answer.'
    def run(self,state):
        task=self.create_task('Synthesize final answer'); rec=state.recommendations[0] if state.recommendations else None; opp=state.opportunities[0] if state.opportunities else None; pred=state.predictions[0] if state.predictions else None
        lines=[f"Agentic answer for {state.request.scope_type} {state.request.scope_id}:", '']
        if rec: lines.append('Recommended action: '+str(rec.get('action_text')))
        elif opp: lines.append(f"Top opportunity: {opp.get('title')} — {opp.get('description')}")
        elif pred: lines.append(f"Prediction signal: {pred.get('prediction_type')} — {pred.get('explanation')}")
        else: lines.append('No recommendation was generated yet. Run feature, prediction, opportunity, and recommendation agents.')
        lines += ['', f'Evidence used: {len(state.evidence)} items.', 'Reasoning path:'] + ['- '+s for s in state.reasoning_steps[-8:]]
        if state.errors: lines += ['', 'Non-blocking issues observed:'] + ['- '+e for e in state.errors[-3:]]
        state.answer='\n'.join(lines); state.confidence=0.85 if state.evidence else 0.55; state.current_agent=self.name; state.tasks.append(self.complete_task(task, {'answer_length': len(state.answer)})); return state
