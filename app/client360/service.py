from __future__ import annotations

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
                    "severity": r.get("severity"),
                    "confidence": r.get("confidence"),
                    "estimated_revenue_impact": r.get("estimated_revenue_impact"),
                    "status": r.get("status"),
                })

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
            "evidence": {
                "source": "phx_dm_household + household_owns_account/holds_product + "
                          "transaction_for_household + recommendation_for_household",
            },
        }
