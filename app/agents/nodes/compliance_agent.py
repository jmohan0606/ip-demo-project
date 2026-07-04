from __future__ import annotations

from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence


class ComplianceAgent(BaseAgent):
    """Rule-based compliance review of every generated recommendation. Real checks,
    not a stamp: each rule inspects the actual recommendation content/figures and a
    failed rule changes the recommendation's status and surfaces the reason.

    COMP-001  Prohibited performance claims (blocked outright).
    COMP-002  Managed/advisory product actions must include suitability + documentation steps.
    COMP-003  Material estimated impact requires supervisory principal review.
    COMP-004  Low model confidence requires human review before client outreach.
    """

    name = 'compliance_agent'
    description = 'Runs rule-based compliance checks on generated recommendations.'

    PROHIBITED_CLAIMS = [
        'guaranteed return', 'risk free', 'risk-free', 'no risk', 'certain profit',
        'cannot lose', 'must buy', 'sure thing',
    ]
    ADVISORY_PRODUCT_TERMS = ['managed', 'advisory', 'mandate', 'discretionary']
    SUITABILITY_TERMS = ['suitability', 'risk profile']
    MATERIAL_IMPACT_USD = 50_000.0
    MIN_CONFIDENCE = 0.60
    RULES_EVALUATED = ['COMP-001', 'COMP-002', 'COMP-003', 'COMP-004']

    def _review_one(self, rec: dict) -> dict:
        text = ' '.join(str(rec.get(k) or '') for k in ('title', 'action_text', 'rationale')).lower()
        flags: list[dict] = []

        for term in self.PROHIBITED_CLAIMS:
            if term in text:
                flags.append({'rule': 'COMP-001', 'level': 'BLOCK',
                              'detail': f'Prohibited performance claim: "{term}"'})

        advisory_hit = [t for t in self.ADVISORY_PRODUCT_TERMS if t in text]
        if advisory_hit and not any(t in text for t in self.SUITABILITY_TERMS):
            flags.append({'rule': 'COMP-002', 'level': 'DISCLOSURE',
                          'detail': (f'Advisory/managed product action ({", ".join(advisory_hit)}) lacks an '
                                     'explicit suitability/risk-profile step — add suitability documentation '
                                     'before client contact.')})

        impact = float(rec.get('estimated_revenue_impact') or 0)
        if impact >= self.MATERIAL_IMPACT_USD:
            flags.append({'rule': 'COMP-003', 'level': 'REVIEW',
                          'detail': (f'Estimated revenue impact ${impact:,.2f} meets the '
                                     f'${self.MATERIAL_IMPACT_USD:,.0f} materiality threshold — supervisory '
                                     'principal review required before execution.')})

        confidence = rec.get('confidence')
        if confidence is not None and float(confidence) < self.MIN_CONFIDENCE:
            flags.append({'rule': 'COMP-004', 'level': 'REVIEW',
                          'detail': (f'Model confidence {float(confidence):.2f} is below the '
                                     f'{self.MIN_CONFIDENCE:.2f} guardrail — human review required before '
                                     'client outreach.')})

        levels = {f['level'] for f in flags}
        status = ('BLOCKED' if 'BLOCK' in levels
                  else 'NEEDS_DISCLOSURE' if 'DISCLOSURE' in levels
                  else 'NEEDS_REVIEW' if 'REVIEW' in levels
                  else 'PASSED')
        return {'recommendation_id': rec.get('recommendation_id'), 'status': status,
                'flags': flags, 'rules_evaluated': self.RULES_EVALUATED}

    def run(self, state):
        task = self.create_task('Run compliance checks on recommendations')
        try:
            reviews = []
            for rec in state.recommendations:
                review = self._review_one(rec)
                rec['compliance'] = review
                rec['compliance_status'] = review['status']
                reviews.append(review)
                if review['status'] != 'PASSED':
                    state.evidence.append(AgentEvidence(
                        source='Compliance Agent',
                        title=f"{review['status']}: {rec.get('recommendation_id')}",
                        content='; '.join(f"[{f['rule']}] {f['detail']}" for f in review['flags']),
                        metadata=review,
                    ))
            counts: dict[str, int] = {}
            for review in reviews:
                counts[review['status']] = counts.get(review['status'], 0) + 1
            state.context['compliance_review'] = {'reviews': reviews, 'status_counts': counts,
                                                  'rules_evaluated': self.RULES_EVALUATED}
            state.reasoning_steps.append(
                'Compliance Agent reviewed '
                f'{len(reviews)} recommendation(s) against {len(self.RULES_EVALUATED)} rules: '
                + (', '.join(f'{status} x{count}' for status, count in sorted(counts.items())) or 'none to review')
                + '.'
            )
            state.tasks.append(self.complete_task(task, {'reviewed': len(reviews), 'status_counts': counts}))
        except Exception as e:
            state.errors.append(str(e))
            state.tasks.append(self.fail_task(task, e))
        return state
