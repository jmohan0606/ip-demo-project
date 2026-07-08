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

    # Agents included on EVERY route regardless of question content.
    ALWAYS = ['context_retrieval_agent', 'tigergraph_graph_agent',
              'explainability_agent', 'ai_assistant_agent']

    # Declarative routing rules — the SINGLE source of truth for both run() below and
    # the /agentic-ai/topology endpoint's agent-graph visualization. Each rule:
    # (question keywords, requested_capability, agents added to the route).
    ROUTING_RULES = [
        (['policy', 'document', 'knowledge', 'playbook'], 'rag', ['rag_knowledge_agent']),
        (['revenue', 'nnm', 'aum', 'fee', 'production', 'product mix', 'managed', 'trend', 'peer'],
         'revenue', ['revenue_agent']),
        (['predict', 'risk', 'score', 'forecast', 'decline', 'growth'], 'prediction', ['prediction_agent']),
        (['opportunity', 'gap', 'focus'], 'opportunity', ['opportunity_agent']),
        (['recommend', 'next best', 'action', 'do next'], 'recommendation', ['recommendation_agent']),
        # Coaching needs real artifacts to ground the card in.
        (['coach', 'improve', 'develop', 'talk track', 'shoutout', '1:1', 'game plan'],
         'coaching', ['opportunity_agent', 'recommendation_agent', 'coaching_agent']),
        (['compliance', 'disclosure', 'suitability', 'guardrail', 'audit'],
         'compliance', ['recommendation_agent', 'rag_knowledge_agent']),
        (['feedback', 'accepted', 'rejected', 'learning'], 'feedback', ['feedback_learning_agent']),
    ]

    # Guardrail invariant: every recommendation run gets a compliance review.
    INVARIANTS = [('recommendation_agent', 'compliance_agent')]

    def run(self, state):
        task = self.create_task('Plan route')
        q = state.request.question.lower()
        req = {x.lower() for x in state.request.requested_capabilities}
        selected = set(self.ALWAYS)

        for keywords, capability, agents in self.ROUTING_RULES:
            if any(k in q for k in keywords) or capability in req:
                selected.update(agents)
        for trigger, required in self.INVARIANTS:
            if trigger in selected:
                selected.add(required)

        route = [name for name in self.ORDER if name in selected]
        state.route_plan = route
        state.reasoning_steps.append('Supervisor selected route: ' + ' -> '.join(route))
        state.tasks.append(self.complete_task(task, {'route_plan': route}))
        return state
