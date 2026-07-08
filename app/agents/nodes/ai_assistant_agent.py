from app.agents.core.base_agent import BaseAgent
from app.llm.client import get_llm_client


class AiAssistantAgent(BaseAgent):
    name = 'ai_assistant_agent'
    description = 'Synthesizes the final answer via the LLM over assembled evidence.'

    def run(self, state):
        task = self.create_task('Synthesize final answer')
        rec = state.recommendations[0] if state.recommendations else None
        opp = state.opportunities[0] if state.opportunities else None
        pred = state.predictions[0] if state.predictions else None

        # Assemble the same structured context the templated version drew on, then
        # let the LLM author the prose (Section-2 adapter: mock | claude | real).
        context = {
            "system_prompt": (
                "You are the iPerform Insights & Coaching assistant for a wealth-management firm. "
                "Write a concise, specific answer to the advisor's question using ONLY the evidence "
                "provided. Lead with the single most important action, cite concrete figures/ids from "
                "the evidence, and do not invent data. 4-6 sentences."
            ),
            "scope": f"{state.request.scope_type} {state.request.scope_id}",
            "persona": state.request.persona,
        }
        if rec:
            context["top_recommendation"] = (
                f"{rec.get('title')} — {rec.get('action_text')} "
                f"(priority {rec.get('priority_score', rec.get('score'))}, "
                f"est_impact {rec.get('estimated_revenue_impact')})"
            )
        if opp:
            context["top_opportunity"] = (
                f"{opp.get('opportunity_type', opp.get('title'))}: "
                f"{opp.get('impact_summary', opp.get('description'))}"
            )
        if pred:
            context["top_prediction"] = (
                f"{pred.get('prediction_type')} score {pred.get('score')}: {pred.get('explanation')}"
            )
        context["evidence_items"] = "; ".join(
            f"{e.source}: {e.title}" for e in state.evidence[:8]
        ) or "no evidence retrieved"
        context["reasoning_path"] = " -> ".join(state.reasoning_steps[-6:])

        prompt = f"Advisor question: {state.request.question}\n\nWrite the answer."

        try:
            answer = get_llm_client().generate(prompt, context)
            self.complete_task(task, {"answer_length": len(answer), "authored_by": "llm"})
        except Exception as exc:
            # Safety net only — keep the workflow alive if the LLM call errors. This is a
            # visible degradation (recorded in state.errors), not a silent mock swap: mock
            # mode already routes through the LLMClient above and is the intended default.
            answer = self._fallback_text(state, rec, opp, pred)
            state.errors.append(f"LLM composer error, used deterministic fallback: {exc}")
            self.complete_task(task, {"answer_length": len(answer), "authored_by": "fallback"})

        state.answer = answer
        state.confidence = self._compute_confidence(state, task.result.get("authored_by") == "llm")
        state.current_agent = self.name
        state.tasks.append(task)
        return state

    @staticmethod
    def _compute_confidence(state, llm_authored: bool) -> float:
        """Composite run confidence from measurable run properties — replaces the
        earlier hardcoded 0.85/0.55. Components (each 0..1, weights sum to 1):
        agent task success rate (0.35), evidence coverage vs a 6-item target
        (0.30), whether the answer was LLM-authored vs deterministic fallback
        (0.15), and the mean model confidence of any predictions produced
        (0.20; neutral 0.70 when the route ran no prediction model). The
        breakdown is persisted to state.context for the observability UI."""
        tasks = [t for t in state.tasks if t.agent_name != 'supervisor']
        task_success = (sum(1 for t in tasks if t.status == 'completed') / len(tasks)) if tasks else 0.0
        evidence_coverage = min(1.0, len(state.evidence) / 6)
        pred_confs = [float(p['confidence']) for p in state.predictions
                      if isinstance(p.get('confidence'), (int, float))]
        model_confidence = sum(pred_confs) / len(pred_confs) if pred_confs else 0.70
        components = {
            'task_success_rate': round(task_success, 4),
            'evidence_coverage': round(evidence_coverage, 4),
            'llm_authored': llm_authored,
            'model_confidence': round(model_confidence, 4),
            'model_confidence_source': f'mean of {len(pred_confs)} prediction(s)' if pred_confs else 'neutral prior (no prediction in route)',
        }
        confidence = round(
            0.35 * task_success + 0.30 * evidence_coverage
            + 0.15 * (1.0 if llm_authored else 0.4) + 0.20 * model_confidence, 4)
        state.context['confidence_breakdown'] = {
            'confidence': confidence, 'components': components,
            'formula': '0.35*task_success + 0.30*evidence_coverage + 0.15*llm_authored + 0.20*model_confidence',
        }
        return confidence

    @staticmethod
    def _fallback_text(state, rec, opp, pred) -> str:
        lines = [f"Answer for {state.request.scope_type} {state.request.scope_id}:", ""]
        if rec:
            lines.append("Recommended action: " + str(rec.get("action_text")))
        elif opp:
            lines.append(
                f"Top opportunity: {opp.get('opportunity_type', opp.get('title'))} — "
                f"{opp.get('impact_summary', opp.get('description'))}"
            )
        elif pred:
            lines.append(f"Prediction signal: {pred.get('prediction_type')} — {pred.get('explanation')}")
        else:
            lines.append("No recommendation was generated for this route.")
        lines += ["", f"Evidence used: {len(state.evidence)} items."]
        return "\n".join(lines)
