from __future__ import annotations

from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.agents.tools.service_tools import AgentToolbox
from app.llm.client import get_llm_client


class CoachingAgent(BaseAgent):
    """Authors the AI Coaching Card (Recommendation / Shoutout / Action Steps /
    Guideline Basis — the mockup pattern) via the LLMClient adapter, grounded in the
    advisor's real feature snapshot, predictions, opportunities, recommendations and
    the compliance review — never templated text."""

    name = 'coaching_agent'
    description = 'Authors the AI Coaching Card for the advisor via the LLM over pipeline artifacts.'

    def __init__(self):
        self.tools = AgentToolbox()

    def run(self, state):
        task = self.create_task('Author AI Coaching Card')
        if state.request.scope_type != 'Advisor':
            state.reasoning_steps.append('Coaching Agent skipped: scope is not a single advisor.')
            state.tasks.append(self.complete_task(task, {'skipped': True}))
            return state
        try:
            advisor_id = state.request.scope_id
            # Ground in artifacts already produced this run; fetch only what's missing.
            recs = state.recommendations or self.tools.run_recommendations(advisor_id)
            opps = state.opportunities or self.tools.run_opportunities(advisor_id)
            preds = state.predictions or self.tools.run_predictions(advisor_id)

            from app.features.engineering import FeatureEngineeringService
            snapshot = FeatureEngineeringService().compute_advisor_snapshot(advisor_id)
            vals = snapshot.values()

            positives = []
            if float(vals.get('revenue_growth_3m_pct') or 0) > 0:
                positives.append(f"revenue up {vals['revenue_growth_3m_pct']}% over the prior 3 months")
            if float(vals.get('nnm_3m') or 0) > 0:
                positives.append(f"positive net new money of ${float(vals['nnm_3m']):,.0f} in the last 3 months")
            if float(vals.get('recommendation_acceptance_rate') or 0) >= 80:
                positives.append(f"{vals['recommendation_acceptance_rate']}% recommendation acceptance rate")
            if float(vals.get('product_diversification_score') or 0) >= 0.9:
                positives.append(f"strong product diversification ({vals['product_diversification_score']})")
            if float(vals.get('milestone_attainment_pct') or 0) >= 90:
                positives.append(f"AGP milestone attainment at {vals['milestone_attainment_pct']}%")

            top_rec = recs[0] if recs else None
            top_opp = opps[0] if opps else None
            top_pred = preds[0] if preds else None
            compliance = (top_rec or {}).get('compliance')

            context = {
                'system_prompt': (
                    'You are the iPerform coaching engine for a wealth-management firm. Write an AI '
                    'Coaching Card for this advisor with EXACTLY these four markdown sections, in this '
                    'order: "## Recommendation" (the single most important coaching move, 2-3 sentences, '
                    'cite the concrete figures provided), "## Shoutout" (genuine recognition grounded ONLY '
                    'in the positive signals provided; if none were provided, acknowledge effort honestly '
                    'without inventing wins), "## Action Steps" (3-4 numbered, concrete steps derived from '
                    'the recommended action and opportunity evidence), "## Guideline Basis" (which playbook '
                    'and compliance/suitability guardrails this guidance rests on, citing the playbook id '
                    'and compliance status provided). Use only the data provided — never invent figures.'
                ),
                'advisor': advisor_id,
                'feature_snapshot': snapshot.snapshot_id,
                'key_metrics': ', '.join(
                    f'{k}={vals.get(k)}' for k in (
                        'revenue_ltm', 'revenue_growth_3m_pct', 'managed_revenue_ratio',
                        'peer_revenue_gap_pct', 'kpi_on_track_ratio', 'overdue_followup_count',
                        'crm_pipeline_value', 'agp_risk_score')
                    if vals.get(k) is not None
                ),
                'positive_signals': '; '.join(positives) or 'none detected this period',
            }
            if top_rec:
                context['top_recommendation'] = (
                    f"{top_rec.get('title')} — {top_rec.get('action_text')} "
                    f"(priority {top_rec.get('priority_score')}, est_impact "
                    f"${float(top_rec.get('estimated_revenue_impact') or 0):,.2f}, "
                    f"playbook {top_rec.get('playbook_id')})"
                )
            if top_opp:
                context['top_opportunity'] = (
                    f"{top_opp.get('category')}: score {top_opp.get('score')}, severity "
                    f"{top_opp.get('severity')}, evidence {top_opp.get('evidence')}"
                )
            if top_pred:
                context['top_prediction'] = (
                    f"{top_pred.get('prediction_type')} score {top_pred.get('score')}: "
                    f"{top_pred.get('explanation')}"
                )
            if compliance:
                context['compliance_review'] = (
                    f"status {compliance['status']}; "
                    + ('; '.join(f"[{f['rule']}] {f['detail']}" for f in compliance['flags'])
                       or 'all rules passed')
                )

            prompt = f'Write the AI Coaching Card for advisor {advisor_id}.'
            llm = get_llm_client()
            try:
                card_markdown = llm.generate(prompt, context)
                authored_by = llm.describe()
            except Exception as exc:
                # Visible degradation, not a silent mock swap (mock mode already goes
                # through the adapter above).
                card_markdown = self._fallback_card(advisor_id, top_rec, positives)
                authored_by = {'mode': 'fallback', 'error': str(exc)}
                state.errors.append(f'Coaching card LLM error, used deterministic fallback: {exc}')

            card = {
                'card_markdown': card_markdown,
                'authored_by': authored_by,
                'grounding': {
                    'feature_snapshot_id': snapshot.snapshot_id,
                    'recommendation_id': (top_rec or {}).get('recommendation_id'),
                    'opportunity_id': (top_opp or {}).get('opportunity_id'),
                    'prediction_id': (top_pred or {}).get('prediction_id'),
                    'playbook_id': (top_rec or {}).get('playbook_id'),
                    'compliance_status': (compliance or {}).get('status'),
                    'positive_signals': positives,
                },
            }
            state.context['coaching_card'] = card
            state.evidence.append(AgentEvidence(
                source='Coaching Agent',
                title=f'AI Coaching Card for {advisor_id}',
                content=card_markdown[:400],
                metadata=card['grounding'],
            ))
            state.reasoning_steps.append(
                f'Coaching Agent authored the coaching card via {authored_by.get("mode")} LLM, grounded in '
                f'{snapshot.snapshot_id}, {len(recs)} recommendation(s), {len(opps)} opportunity(ies) and '
                f'{len(positives)} positive signal(s).'
            )
            state.tasks.append(self.complete_task(task, {
                'card_length': len(card_markdown), 'authored_by': authored_by.get('mode'),
                'grounding': card['grounding'],
            }))
        except Exception as e:
            state.errors.append(str(e))
            state.tasks.append(self.fail_task(task, e))
        return state

    @staticmethod
    def _fallback_card(advisor_id: str, top_rec: dict | None, positives: list[str]) -> str:
        lines = [f'## Recommendation',
                 (top_rec or {}).get('action_text') or 'No open recommendation this period.',
                 '## Shoutout',
                 ('; '.join(positives) or 'Keep executing — no standout positive signals this period.'),
                 '## Action Steps',
                 '1. Review the open recommendation and its evidence.',
                 '## Guideline Basis',
                 f"Playbook {(top_rec or {}).get('playbook_id')}, compliance status "
                 f"{((top_rec or {}).get('compliance') or {}).get('status', 'not reviewed')}."]
        return '\n'.join(lines)
