"""GraphReasoner — genuine graph-based relational reasoning over the temporal knowledge graph.

This is the capability the flat context bundle lacked:
  1. REASONING-TRACE REUSE — before answering, retrieve PRIOR reasoning traces for the
     advisor/scope by graph traversal (phx_dm_reasoning_for_advisor) and feed them into the new
     answer, so the agent builds on past conclusions ("experience memory"). After answering, it
     records a new trace linked back to the advisor for the next question to reuse.
  2. MULTI-HOP TRAVERSAL — for an advisor question it walks
     advisor → households → open opportunities, and advisor → similar advisors (similarity edges,
     with scores) → those peers' successful action families; for a scope question it walks
     scope → advisors → households → aggregated real outcomes. Every hop is the REAL traversal of
     the loaded graph (via the registered traversal queries), and the exact path (entities
     visited, edges walked) is returned for grounding and for the Explainability view.

All reads/writes go through get_graph_client() (mock traversal queries now; installed GSQL in
real mode) — the traversal is never LLM-narrated.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.graph.artifacts import write_reasoning_trace
from app.graph.client import get_graph_client
from app.shared.ids import timestamp_id
from app.shared.logging import get_logger

_log = get_logger("app.reasoning")


class GraphReasoner:
    def __init__(self) -> None:
        self.graph = get_graph_client()

    def _rows(self, query: str, params: dict) -> list[dict]:
        try:
            res = self.graph.run_query(query, params)
            return res.get("results", []) if isinstance(res, dict) else (res or [])
        except Exception as exc:  # noqa: BLE001 — reasoning augmentation must never break the answer
            _log.warning("reasoning query %s failed: %s", query, exc)
            return []

    # -- item 1: prior reasoning-trace retrieval (experience memory) ---------
    def prior_reasoning(self, scope_id: str, limit: int = 3) -> list[dict]:
        """Prior reasoning traces for this advisor, newest first, by graph traversal of
        phx_dm_reasoning_for_advisor."""
        rows = self._rows("get_reasoning_traces_for_scope", {"scope_id": scope_id, "result_limit": limit})
        out = []
        for r in rows:
            steps = r.get("reasoning_steps_json") or "[]"
            try:
                steps = json.loads(steps) if isinstance(steps, str) else steps
            except json.JSONDecodeError:
                steps = []
            out.append({"reasoning_id": r.get("reasoning_id"), "created_at": r.get("created_at"),
                        "conclusion": (steps[-1] if steps else ""), "steps": steps})
        return out

    def record_reasoning(self, scope_type: str, scope_id: str, steps: list[str], evidence: dict) -> str:
        """Persist a new reasoning trace anchored to the advisor (ADVISOR artifact →
        phx_dm_reasoning_for_advisor edge) so the NEXT question can retrieve and build on it."""
        reasoning_id = timestamp_id("REASONc")
        # anchor to advisor when the scope resolves to one; else record without the advisor edge.
        artifact_type = "ADVISOR" if scope_type.upper() == "ADVISOR" else "SCOPE"
        try:
            write_reasoning_trace(self.graph, reasoning_id, artifact_type, scope_id, steps, evidence,
                                  created_at=datetime.now(timezone.utc).isoformat())
        except Exception as exc:  # noqa: BLE001
            _log.warning("record_reasoning failed: %s", exc)
        return reasoning_id

    # -- item 2: multi-hop traversal reasoning ------------------------------
    def advisor_traversal(self, advisor_id: str) -> dict:
        rows = self._rows("advisor_reasoning_traversal", {"advisor_id": advisor_id})
        return rows[0] if rows else {}

    def scope_traversal(self, scope_type: str, scope_id: str) -> dict:
        rows = self._rows("scope_reasoning_traversal", {"scope_type": scope_type, "scope_id": scope_id})
        return rows[0] if rows else {}

    # -- render traversal + prior reasoning as grounded prompt context ------
    @staticmethod
    def render_advisor_reasoning(trav: dict, priors: list[dict]) -> str:
        if not trav:
            return ""
        lines = [f"Relational graph traversal for {trav.get('advisor_name', trav.get('advisor_id'))} "
                 f"({trav.get('hops', 0)} hops walked):"]
        opps = [o for h in trav.get("households", []) for o in h.get("open_opportunities", [])]
        lines.append(f"- This advisor's {len(trav.get('households', []))} households have "
                     f"{trav.get('total_open_opportunities', 0)} OPEN opportunities"
                     + (f" (e.g. {opps[0].get('type')} on a household)" if opps else "") + ".")
        for s in trav.get("similar_advisors", []):
            fam = s.get("successful_families") or []
            top = fam[0] if fam else None
            lines.append(f"- Similar advisor {s.get('name')} (similarity {round(s.get('similarity_score', 0), 2)}): "
                         + (f"strongest action family {top['family']} "
                            f"(proven {top['proven']}x, est. impact ${top['impact']:,.0f})" if top else "no action history"))
        pats = trav.get("peer_success_patterns", [])
        if pats:
            lines.append("- Action families that worked across similar advisors: "
                         + ", ".join(f"{p['family']} (proven {p['proven']}x, ${p['total_impact']:,.0f})" for p in pats[:3]))
        if priors:
            lines.append("Prior reasoning for this advisor (build on it, do not restate cold):")
            for p in priors:
                lines.append(f"  · earlier ({(p.get('created_at') or '')[:10]}): {p.get('conclusion')}")
        return "\n".join(lines)

    @staticmethod
    def render_scope_reasoning(trav: dict) -> str:
        if not trav:
            return ""
        lines = [f"Relational graph traversal across {trav.get('scope_type')} {trav.get('scope_id')} "
                 f"({trav.get('hops', 0)} hops): {trav.get('advisor_count', 0)} advisors → "
                 f"{trav.get('household_count', 0)} households → {trav.get('total_open_opportunities', 0)} open opportunities."]
        lines.append("Top contributing advisors found by traversal (name · households · open opps · recorded impact):")
        for c in trav.get("top_contributors", [])[:5]:
            lines.append(f"  · {c.get('name')} ({c.get('advisor_id')}) · {c.get('households')} hh · "
                         f"{c.get('open_opportunities')} opps · ${c.get('recorded_impact', 0):,.0f}")
        return "\n".join(lines)
