from __future__ import annotations

from datetime import date, timedelta

from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.graph.client import get_graph_client


class RevenueAgent(BaseAgent):
    """Revenue-specific analysis over GraphClient: LTM summary + 3-month momentum
    (GQ-004), monthly trend direction (GQ-005), product-mix concentration and
    managed share (GQ-006), and peer benchmark gap/percentile (GQ-008)."""

    name = 'revenue_agent'
    description = 'Analyzes revenue trend, product mix and peer position for the scoped advisor.'

    AS_OF = date(2026, 7, 3)  # deterministic anchor aligned with seed data

    def _window(self, months: int) -> tuple[str, str]:
        end = self.AS_OF.replace(day=1) - timedelta(days=1)  # last complete month end
        start = (end.replace(day=1) - timedelta(days=months * 31 - 15)).replace(day=1)
        return start.isoformat(), end.isoformat()

    @staticmethod
    def _merged(graph, query: str, params: dict) -> dict:
        merged: dict = {}
        for entry in graph.run_query(query, params).get('results', []):
            merged.update(entry)
        return merged

    def run(self, state):
        task = self.create_task('Analyze revenue')
        if state.request.scope_type != 'Advisor':
            state.reasoning_steps.append('Revenue Agent skipped: scope is not a single advisor.')
            state.tasks.append(self.complete_task(task, {'skipped': True}))
            return state
        try:
            graph = get_graph_client()
            advisor_id = state.request.scope_id
            start, end = self._window(12)
            scope = {'scope_type': 'ADVISOR', 'scope_id': advisor_id, 'start_date': start, 'end_date': end}

            summary = self._merged(graph, 'get_revenue_summary_by_scope', {**scope, 'period_type': 'CUSTOM'})
            revenue_ltm = float(summary.get('total_revenue') or 0)

            trend = self._merged(graph, 'get_revenue_trend_by_scope', {**scope, 'period_grain': 'MONTH'})
            months = [row for row in trend.get('revenue_trend', []) if row.get('revenue') is not None]
            last_3 = [r['revenue'] for r in months[-3:]]
            prior_3 = [r['revenue'] for r in months[-6:-3]]
            momentum_pct = (
                round((sum(last_3) - sum(prior_3)) / sum(prior_3) * 100, 2) if sum(prior_3) else 0.0
            )
            direction = 'up' if momentum_pct > 2 else 'down' if momentum_pct < -2 else 'flat'

            mix = self._merged(graph, 'get_product_mix_by_scope', scope)
            managed_ids = {
                p['v_id'] for p in mix.get('products', []) if p.get('attributes', {}).get('managed_flag')
            }
            mix_rows = mix.get('product_mix', [])
            total_mix_rev = sum(float(r.get('revenue') or 0) for r in mix_rows)
            managed_rev = sum(
                float(r.get('revenue') or 0) for r in mix_rows if r.get('product_id') in managed_ids
            )
            managed_ratio = round(managed_rev / total_mix_rev, 4) if total_mix_rev else 0.0
            top_products = [
                {'product_id': r['product_id'], 'product_name': r.get('product_name'), 'revenue': r['revenue']}
                for r in mix_rows[:3]
            ]

            peer = self._merged(graph, 'get_peer_benchmark',
                                {'advisor_id': advisor_id, 'peer_method': 'MARKET',
                                 'start_date': start, 'end_date': end})
            peers = peer.get('peers', [])
            peer_avg = round(peer['peer_revenue_sum'] / peer['peer_count'], 2) if peer.get('peer_count') else 0.0
            peer_gap_pct = round((revenue_ltm - peer_avg) / peer_avg * 100, 2) if peer_avg else 0.0
            percentile = (
                round(sum(1 for p in peers if p['revenue'] < revenue_ltm) / len(peers) * 100) if peers else None
            )

            analysis = {
                'advisor_id': advisor_id,
                'window': {'start': start, 'end': end},
                'revenue_ltm': revenue_ltm,
                'ending_aum': summary.get('ending_aum'),
                'total_nnm': summary.get('total_nnm'),
                'total_ncf': summary.get('total_ncf'),
                'momentum_3m_pct': momentum_pct,
                'trend_direction': direction,
                'trend_months_used': len(months),
                'managed_revenue_ratio': managed_ratio,
                'managed_revenue': round(managed_rev, 2),
                'top_products': top_products,
                'peer_avg_revenue': peer_avg,
                'peer_gap_pct': peer_gap_pct,
                'peer_percentile': percentile,
                'peer_count': peer.get('peer_count'),
                'sources': ['GQ-004 get_revenue_summary_by_scope', 'GQ-005 get_revenue_trend_by_scope',
                            'GQ-006 get_product_mix_by_scope', 'GQ-008 get_peer_benchmark'],
            }
            state.context['revenue_analysis'] = analysis
            state.evidence.append(AgentEvidence(
                source='Revenue Agent',
                title=f'Revenue analysis for {advisor_id}',
                content=(
                    f"LTM revenue ${revenue_ltm:,.2f}, 3-month momentum {momentum_pct:+.1f}% ({direction}); "
                    f"managed share {managed_ratio:.1%}; peer avg ${peer_avg:,.2f} "
                    f"(gap {peer_gap_pct:+.1f}%, percentile {percentile})"
                ),
                score=momentum_pct,
                metadata=analysis,
            ))
            state.reasoning_steps.append(
                f'Revenue Agent: LTM ${revenue_ltm:,.0f}, momentum {momentum_pct:+.1f}% ({direction}), '
                f'peer gap {peer_gap_pct:+.1f}% over {peer.get("peer_count")} market peers.'
            )
            state.tasks.append(self.complete_task(task, {
                'revenue_ltm': revenue_ltm, 'momentum_3m_pct': momentum_pct,
                'peer_gap_pct': peer_gap_pct, 'managed_revenue_ratio': managed_ratio,
            }))
        except Exception as e:
            state.errors.append(str(e))
            state.tasks.append(self.fail_task(task, e))
        return state
