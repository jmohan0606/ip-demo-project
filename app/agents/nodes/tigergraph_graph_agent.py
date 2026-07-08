from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.agents.tools.service_tools import AgentToolbox


class TigerGraphGraphAgent(BaseAgent):
    """Traverses the real graph (tiered client: MCP → pyTigerGraph → RESTPP → mock/
    foundation store) for the scoped advisor's actual neighborhood — households,
    accounts, CRM, AGP, AI artifacts — and reports the real per-run figures plus
    which tier actually served the query. No boilerplate: the evidence content IS
    the retrieved data."""

    name = 'tigergraph_graph_agent'
    description = 'Queries TigerGraph through MCP-first graph access.'

    def __init__(self):
        self.tools = AgentToolbox()

    @staticmethod
    def _attr(vertex_list, key):
        if vertex_list and isinstance(vertex_list, list):
            return (vertex_list[0].get('attributes') or {}).get(key)
        return None

    def run(self, state):
        task = self.create_task('Query graph evidence')
        try:
            health = self.tools.graph_health()
            state.context['graph_health'] = health

            if state.request.scope_type != 'Advisor':
                state.reasoning_steps.append('TigerGraph Graph Agent skipped traversal: scope is not a single advisor.')
                state.tasks.append(self.complete_task(task, {'skipped': True, 'active_mode': health.get('active_mode')}))
                return state

            advisor_id = state.request.scope_id
            result = self.tools.graph_query_advisor_evidence(advisor_id)
            row = (result.get('results') or [{}])[0]
            served_by = result.get('served_by') or health.get('active_mode') or 'unknown'
            served_by_tier = result.get('served_by_tier')

            counts = {k: len(v) for k, v in row.items() if isinstance(v, list)}
            advisor_name = self._attr(row.get('advisor'), 'advisor_name') or self._attr(row.get('advisor'), 'name') or advisor_id
            branch = self._attr(row.get('branch'), 'branch_name') or self._attr(row.get('branch'), 'name')
            market = self._attr(row.get('market'), 'market_name') or self._attr(row.get('market'), 'name')

            state.context['graph_evidence'] = {
                'query': 'get_advisor_360', 'advisor_id': advisor_id,
                'served_by': served_by, 'served_by_tier': served_by_tier, 'counts': counts,
            }

            parts = []
            for label, key in (('households', 'households'), ('accounts', 'accounts'),
                               ('CRM activities', 'crm_activities'), ('open CRM opportunities', 'crm_opportunities'),
                               ('AGP enrollments', 'enrollments'), ('predictions', 'predictions'),
                               ('AI opportunities', 'opportunities'), ('recommendations', 'recommendations'),
                               ('memories', 'memories'), ('feature snapshots', 'features')):
                if counts.get(key):
                    parts.append(f"{counts[key]} {label}")
            location = ' · '.join(x for x in (branch, market) if x)
            content = (
                f"get_advisor_360 traversal for {advisor_name} ({advisor_id})"
                + (f" — {location}" if location else '') + ': '
                + (', '.join(parts) if parts else 'no connected entities found') + '.'
            )

            state.evidence.append(AgentEvidence(
                source='TigerGraph Graph Access',
                title=f"Advisor neighborhood via tier: {served_by}",
                content=content,
                score=float(sum(counts.values())) or None,
                metadata={'health': health, 'counts': counts, 'served_by': served_by,
                          'served_by_tier': served_by_tier, 'query': 'get_advisor_360'},
            ))
            state.reasoning_steps.append(
                f"TigerGraph Graph Agent traversed {advisor_id}'s neighborhood via {served_by} tier: "
                + (', '.join(parts[:5]) if parts else 'no connected entities') + '.'
            )
            state.tasks.append(self.complete_task(task, {
                'served_by': served_by, 'entities_retrieved': sum(counts.values()), 'counts': counts,
            }))
        except Exception as e:
            state.errors.append(str(e))
            state.tasks.append(self.fail_task(task, e))
        return state
