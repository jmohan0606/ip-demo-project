from app.agents.registry.agent_registry import AgentRegistry
from app.agents.state.agent_state import AgenticRequest, AgenticResponse, AgentWorkflowState
from app.agents.workflows.advisor_coaching_graph import AdvisorCoachingAgentGraph
from app.config.settings import get_settings
from app.shared.ids import timestamp_id


class AgenticAiService:
    def __init__(self):
        self.graph = AdvisorCoachingAgentGraph()
        self.registry = AgentRegistry()
        # Same real guardrail layer the chat path runs (input screen before the
        # supervisor, output screen on the synthesized answer, events persisted to
        # phx_dm_guardrail_event) — previously the agentic path skipped it entirely.
        from app.guardrails.service import GuardrailService
        self.guardrails = GuardrailService() if get_settings().guardrails_enabled else None

    def run(self, request: AgenticRequest) -> AgenticResponse:
        run_id = timestamp_id('agentrun')
        guardrails_report: dict = {}

        if self.guardrails is not None:
            input_gr = self.guardrails.check_input(request.question, execution_id=run_id)
            guardrails_report['input'] = input_gr.model_dump(mode='json')
            if input_gr.blocked:
                return AgenticResponse(
                    run_id=run_id, answer=self.guardrails.safe_refusal(input_gr),
                    final_agent='guardrails', confidence=1.0,
                    reasoning_steps=['Input guardrails BLOCKED the request before any agent ran: '
                                     + input_gr.summary()],
                    guardrails=guardrails_report,
                )

        final = self.graph.run(AgentWorkflowState(request=request, run_id=run_id))

        if self.guardrails is not None:
            evidence_context = '\n'.join(f'{e.source}: {e.title} — {e.content}' for e in final.evidence)
            output_gr = self.guardrails.check_output(final.answer, evidence_context, execution_id=run_id)
            guardrails_report['output'] = output_gr.model_dump(mode='json')
            if output_gr.redacted and output_gr.sanitized_text:
                final.answer = output_gr.sanitized_text

        return AgenticResponse(
            run_id=final.run_id, answer=final.answer, final_agent=final.current_agent,
            tasks=final.tasks, evidence=final.evidence, reasoning_steps=final.reasoning_steps,
            recommendations=final.recommendations, opportunities=final.opportunities,
            predictions=final.predictions, revenue_analysis=final.context.get('revenue_analysis'),
            compliance_review=final.context.get('compliance_review'),
            coaching_card=final.context.get('coaching_card'), confidence=final.confidence,
            confidence_breakdown=final.context.get('confidence_breakdown'),
            route_plan=final.route_plan, graph_evidence=final.context.get('graph_evidence'),
            errors=final.errors, guardrails=guardrails_report or None)

    def list_agents(self):
        return self.registry.list_agents()
