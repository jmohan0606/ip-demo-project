from __future__ import annotations

import json

from app.embeddings.similar_entities import _embeddings_by_entity, similar_entities
from app.graph.client import get_graph_client


class Client360Service:
    """Household (client) 360 profile from the graph: the client, its serving
    advisor, accounts + product holdings, recent transactions, and the AI
    artifacts (prediction/opportunity/recommendation) attached to the household.
    Every value is a real vertex/edge read — no synthesized client data."""

    def __init__(self) -> None:
        self._store = get_graph_client().store

    def _v(self, vtype: str, vid: str) -> dict:
        return self._store.vertex(vtype, vid) or {}

    def _recommendation_lineage(self, rid: str) -> dict:
        """Explain HOW a recommendation was reached (CLAUDE.md 9.5): the addressed
        opportunity, the prediction it is based on, the feature snapshot it used,
        the reasoning steps and the concrete evidence — all from real lineage edges."""
        store = self._store
        sources: list[dict] = []

        for opp_id in store.out_ids("phx_dm_recommendation_addresses_opportunity", rid):
            o = self._v("phx_dm_opportunity", opp_id)
            if o:
                sources.append({
                    "type": "Opportunity",
                    "ref": opp_id,
                    "detail": f"{o.get('category', 'opportunity')} · severity {o.get('severity')} · "
                              f"est. impact ${float(o.get('estimated_revenue_impact') or 0):,.0f}",
                })
        for pred_id in store.out_ids("phx_dm_recommendation_based_on_prediction", rid):
            p = self._v("phx_dm_prediction", pred_id)
            if p:
                sources.append({
                    "type": "Prediction",
                    "ref": pred_id,
                    "detail": f"{p.get('prediction_type', 'prediction')} · score {p.get('score')} · {p.get('explanation', '')}"[:140],
                })
        for fs_id in store.out_ids("phx_dm_recommendation_uses_feature_snapshot", rid):
            sources.append({"type": "Feature Snapshot", "ref": fs_id, "detail": "Phase-5 feature snapshot used as input"})
        for pb_id in store.out_ids("phx_dm_recommendation_uses_playbook", rid):
            pb = self._v("phx_dm_playbook", pb_id)
            sources.append({"type": "Playbook", "ref": pb_id, "detail": pb.get("title") or pb.get("name") or pb_id})

        reasoning_steps: list[str] = []
        evidence: list[dict] = []
        for reason_id in store.in_ids("phx_dm_reasoning_for_recommendation", rid):
            r = self._v("phx_dm_reasoning_trace", reason_id)
            try:
                reasoning_steps = list(json.loads(r.get("reasoning_steps_json") or "[]"))
            except (ValueError, TypeError):
                reasoning_steps = []
            try:
                ev = json.loads(r.get("evidence_json") or "{}")
            except (ValueError, TypeError):
                ev = {}
            # flatten one level of the evidence dict into label/value pairs, skipping
            # id/type plumbing so only real signals surface as evidence
            _skip = {"target_type", "target_id", "feature_snapshot_id", "advisor_id", "household_id"}
            for key, val in (ev.get("features") or ev).items() if isinstance(ev, dict) else []:
                if key not in _skip and isinstance(val, (int, float, str)):
                    evidence.append({"label": key, "value": val})
            break
        return {"sources": sources, "reasoning_steps": reasoning_steps, "evidence": evidence[:8]}

    def households_for_advisor(self, advisor_id: str) -> list[dict]:
        store = self._store
        rows = []
        for hid in store.out_ids("phx_dm_advisor_serves_household", advisor_id):
            a = self._v("phx_dm_household", hid)
            rows.append({
                "household_id": hid,
                "household_name": a.get("household_name", hid),
                "segment": a.get("segment"),
                "total_aum": a.get("total_aum"),
            })
        rows.sort(key=lambda r: float(r.get("total_aum") or 0), reverse=True)
        return rows

    def profile(self, household_id: str) -> dict:
        store = self._store
        hh = self._v("phx_dm_household", household_id)

        advisor_ids = store.in_ids("phx_dm_advisor_serves_household", household_id)
        advisor = self._v("phx_dm_advisor", advisor_ids[0]) if advisor_ids else {}

        accounts = []
        for acc_id in store.out_ids("phx_dm_household_owns_account", household_id):
            a = self._v("phx_dm_account", acc_id)
            holdings = []
            for pid in store.out_ids("phx_dm_account_holds_product", acc_id):
                p = self._v("phx_dm_product", pid)
                holdings.append({
                    "product_id": pid,
                    "product_name": p.get("product_name"),
                    "risk_level": p.get("risk_level"),
                    "managed": bool(p.get("managed_flag")),
                })
            accounts.append({
                "account_id": acc_id,
                "account_name": a.get("account_name"),
                "account_type": a.get("account_type"),
                "status": a.get("status"),
                "opened_date": a.get("opened_date"),
                "current_value": float(a.get("current_value") or 0),
                "holdings": holdings,
            })
        accounts.sort(key=lambda r: r["current_value"], reverse=True)

        # recent transactions across the household
        txns = []
        for tx_id in store.in_ids("phx_dm_transaction_for_household", household_id):
            t = self._v("phx_dm_revenue_transaction", tx_id)
            if t:
                txns.append({
                    "transaction_id": tx_id,
                    "transaction_date": t.get("transaction_date"),
                    "transaction_type": t.get("transaction_type"),
                    "revenue_amount": float(t.get("revenue_amount") or 0),
                    "gross_amount": float(t.get("gross_amount") or 0),
                })
        txns.sort(key=lambda r: str(r.get("transaction_date") or ""), reverse=True)
        total_revenue = round(sum(t["revenue_amount"] for t in txns), 2)

        recs = []
        for rid in store.in_ids("phx_dm_recommendation_for_household", household_id):
            r = self._v("phx_dm_recommendation", rid)
            if r:
                recs.append({
                    "recommendation_id": rid,
                    "title": r.get("title"),
                    "action_text": r.get("action_text"),
                    "recommendation_type": r.get("recommendation_type"),
                    "severity": r.get("severity"),
                    "confidence": r.get("confidence"),
                    "priority_score": r.get("priority_score"),
                    "estimated_revenue_impact": r.get("estimated_revenue_impact"),
                    "impact_summary": r.get("impact_summary"),
                    "status": r.get("status"),
                    # HOW it was reached (evidence + sources + reasoning) per CLAUDE.md 9.5
                    "lineage": self._recommendation_lineage(rid),
                })

        # Similar households / accounts / portfolios — real cosine NN over embeddings.
        hh_emb = _embeddings_by_entity(store, "HOUSEHOLD")
        acct_emb = _embeddings_by_entity(store, "ACCOUNT")
        similar = {
            "households": similar_entities("HOUSEHOLD", household_id, 3) if household_id in hh_emb else None,
            "accounts": None,
        }
        top_acct = next((a["account_id"] for a in accounts if a["account_id"] in acct_emb), None)
        if top_acct:
            similar["accounts"] = similar_entities("ACCOUNT", top_acct, 3)

        managed_value = sum(
            acc["current_value"] for acc in accounts if any(h["managed"] for h in acc["holdings"])
        )
        return {
            "household_id": household_id,
            "household_name": hh.get("household_name", household_id),
            "segment": hh.get("segment"),
            "risk_profile": hh.get("risk_profile"),
            "status": hh.get("status"),
            "state": hh.get("state"),
            "total_aum": float(hh.get("total_aum") or 0),
            "serving_advisor": {
                "advisor_id": advisor_ids[0] if advisor_ids else None,
                "advisor_name": advisor.get("advisor_name"),
            },
            "summary": {
                "account_count": len(accounts),
                "holding_count": sum(len(a["holdings"]) for a in accounts),
                "managed_value": round(managed_value, 2),
                "managed_ratio": round(managed_value / float(hh.get("total_aum") or 1), 4) if hh.get("total_aum") else 0.0,
                "transaction_count": len(txns),
                "revenue_ltm": total_revenue,
            },
            "accounts": accounts,
            "transactions": txns[:15],
            "recommendations": recs,
            "similar": similar,
            "evidence": {
                "source": "phx_dm_household + household_owns_account/holds_product + "
                          "transaction_for_household + recommendation_for_household",
            },
        }
