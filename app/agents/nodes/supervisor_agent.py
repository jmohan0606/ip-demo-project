from app.agents.core.base_agent import BaseAgent


class SupervisorAgent(BaseAgent):
    name = 'supervisor'
    description = 'Routes requests to specialist agents.'

    # Canonical execution order: retrieval first, domain analysis, then artifact
    # generation, compliance ALWAYS after recommendations, coaching after compliance
    # (so the card can cite the compliance verdict), synthesis last.
    ORDER = ['context_retrieval_agent', 'tigergraph_graph_agent', 'rag_knowledge_agent',
             'revenue_agent', 'prediction_agent', 'opportunity_agent', 'recommendation_agent',
             'compliance_agent', 'coaching_agent', 'feedback_learning_agent',
             'explainability_agent', 'ai_assistant_agent']

    def run(self, state):
        task = self.create_task('Plan route')
        q = state.request.question.lower()
        req = {x.lower() for x in state.request.requested_capabilities}
        selected = {'context_retrieval_agent', 'tigergraph_graph_agent',
                    'explainability_agent', 'ai_assistant_agent'}

        if any(x in q for x in ['policy', 'document', 'knowledge', 'playbook']) or 'rag' in req:
            selected.add('rag_knowledge_agent')
        if any(x in q for x in ['revenue', 'nnm', 'aum', 'fee', 'production', 'product mix',
                                'managed', 'trend', 'peer']) or 'revenue' in req:
            selected.add('revenue_agent')
        if any(x in q for x in ['predict', 'risk', 'score', 'forecast', 'decline', 'growth']) or 'prediction' in req:
            selected.add('prediction_agent')
        if any(x in q for x in ['opportunity', 'gap', 'focus']) or 'opportunity' in req:
            selected.add('opportunity_agent')
        if any(x in q for x in ['recommend', 'next best', 'action', 'do next']) or 'recommendation' in req:
            selected.add('recommendation_agent')
        if any(x in q for x in ['coach', 'improve', 'develop', 'talk track', 'shoutout',
                                '1:1', 'game plan']) or 'coaching' in req:
            # Coaching needs real artifacts to ground the card in.
            selected.update(['opportunity_agent', 'recommendation_agent', 'coaching_agent'])
        if any(x in q for x in ['compliance', 'disclosure', 'suitability', 'guardrail', 'audit']) or 'compliance' in req:
            selected.update(['recommendation_agent', 'rag_knowledge_agent'])
        if any(x in q for x in ['feedback', 'accepted', 'rejected', 'learning']) or 'feedback' in req:
            selected.add('feedback_learning_agent')
        # Guardrail invariant: every recommendation run gets a compliance review.
        if 'recommendation_agent' in selected:
            selected.add('compliance_agent')

        route = [name for name in self.ORDER if name in selected]
        state.route_plan = route
        state.reasoning_steps.append('Supervisor selected route: ' + ' -> '.join(route))
        state.tasks.append(self.complete_task(task, {'route_plan': route}))
        return state
