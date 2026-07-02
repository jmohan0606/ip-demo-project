from app.agents.core.base_agent import BaseAgent
class SupervisorAgent(BaseAgent):
    name='supervisor'; description='Routes requests to specialist agents.'
    def run(self,state):
        task=self.create_task('Plan route'); q=state.request.question.lower(); req={x.lower() for x in state.request.requested_capabilities}; route=['context_retrieval_agent','tigergraph_graph_agent']
        if any(x in q for x in ['policy','compliance','document','knowledge']) or 'rag' in req: route.append('rag_knowledge_agent')
        if any(x in q for x in ['predict','risk','score','growth','revenue','nnm','aum']) or 'prediction' in req: route.append('prediction_agent')
        if any(x in q for x in ['opportunity','gap','focus']) or 'opportunity' in req: route.append('opportunity_agent')
        if any(x in q for x in ['recommend','next best','action','do next']) or 'recommendation' in req: route.append('recommendation_agent')
        if any(x in q for x in ['feedback','accepted','rejected','learning']) or 'feedback' in req: route.append('feedback_learning_agent')
        route += ['explainability_agent','ai_assistant_agent']
        final=[]
        for r in route:
            if r not in final: final.append(r)
        state.route_plan=final; state.reasoning_steps.append('Supervisor selected route: '+' -> '.join(final)); state.tasks.append(self.complete_task(task, {'route_plan': final})); return state
