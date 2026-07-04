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
        state.confidence = 0.85 if state.evidence else 0.55
        state.current_agent = self.name
        state.tasks.append(task)
        return state

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
