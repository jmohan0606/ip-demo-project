from __future__ import annotations

import json
import logging

from app.embeddings.similar_entities import _embeddings_by_entity, _parse_vector, similar_entities
from app.graph.client import get_graph_client
from app.graph.queries.common import graph_fallback_store, run_catalog_query

logger = logging.getLogger(__name__)


def _attrs(row: dict) -> dict:
    """RESTPP vset row -> attributes dict (tolerates flat mock rows)."""
    return row.get("attributes", row) if isinstance(row, dict) else {}


def _entry(results: list[dict], key: str) -> dict | None:
    """First result entry carrying `key` (queries PRINT several named sets)."""
    for entry in results:
        if key in entry:
            return entry
    return None


class Client360Service:
    """Household (client) 360 profile from the graph: the client, its serving
    advisor, accounts + product holdings, recent transactions, and the AI
    artifacts (prediction/opportunity/recommendation) attached to the household.
    Every value is a real vertex/edge read — no synthesized client data.

    Reads go through catalogued GQ-### queries via GraphClient.run_query()
    (GQ-011 get_household_360, GQ-012 get_account_holdings_and_activity,
    GQ-010 get_advisor_book_of_business, GQ-029 get_recommendation_detail,
    GQ-024 get_embeddings_for_entity) so tier 2 (real TigerGraph) serves them
    in real mode; the direct store traversal remains ONLY as a logged fallback.
    """

    def __init__(self) -> None:
        self._graph = get_graph_client()

    @property
    def _store(self):
        """FoundationGraphStore used exclusively by the logged fallback paths."""
        return graph_fallback_store(self._graph)

    def _v(self, vtype: str, vid: str) -> dict:
        return self._store.vertex(vtype, vid) or {}

    # ------------------------------------------------------------------ lineage

    def _recommendation_lineage(self, rid: str) -> dict:
        """Explain HOW a recommendation was reached (CLAUDE.md 9.5): the addressed
        opportunity, the prediction it is based on, the feature snapshot it used,
        the reasoning steps and the concrete evidence — all from real lineage edges,
        read via GQ-029 get_recommendation_detail."""
        results = run_catalog_query(
            self._graph, "get_recommendation_detail", {"recommendation_id": rid}
        )
        if results is not None:
            entry = _entry(results, "opportunities")
            if entry is not None:
                return self._lineage_from_query(entry)
            logger.warning(
                "get_recommendation_detail returned no lineage entry for %s — "
                "falling back to local store traversal", rid,
            )
        else:
            logger.warning(
                "get_recommendation_detail unavailable for %s — falling back to "
                "local store traversal", rid,
            )
        return self._recommendation_lineage_store(rid)

    def _lineage_from_query(self, entry: dict) -> dict:
        sources: list[dict] = []
        for row in entry.get("opportunities") or []:
            o = _attrs(row)
            if o:
                sources.append({
                    "type": "Opportunity",
                    "ref": row.get("v_id"),
                    "detail": f"{o.get('category', 'opportunity')} · severity {o.get('severity')} · "
                              f"est. impact ${float(o.get('estimated_revenue_impact') or 0):,.0f}",
                })
        for row in entry.get("predictions") or []:
            p = _attrs(row)
            if p:
                sources.append({
                    "type": "Prediction",
                    "ref": row.get("v_id"),
                    "detail": f"{p.get('prediction_type', 'prediction')} · score {p.get('score')} · {p.get('explanation', '')}"[:140],
                })
        for row in entry.get("features") or []:
            sources.append({"type": "Feature Snapshot", "ref": row.get("v_id"), "detail": "Phase-5 feature snapshot used as input"})
        for row in entry.get("playbooks") or []:
            pb = _attrs(row)
            sources.append({"type": "Playbook", "ref": row.get("v_id"), "detail": pb.get("title") or pb.get("name") or row.get("v_id")})

        reasoning_rows = entry.get("reasoning") or []
        reasoning_steps, evidence = self._parse_reasoning(_attrs(reasoning_rows[0]) if reasoning_rows else None)
        return {"sources": sources, "reasoning_steps": reasoning_steps, "evidence": evidence[:8]}

    @staticmethod
    def _parse_reasoning(r: dict | None) -> tuple[list[str], list[dict]]:
        """reasoning_steps + flattened evidence from one phx_dm_reasoning_trace."""
        reasoning_steps: list[str] = []
        evidence: list[dict] = []
        if r is None:
            return reasoning_steps, evidence
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
        return reasoning_steps, evidence

    def _recommendation_lineage_store(self, rid: str) -> dict:
        """Logged fallback: the original direct store traversal."""
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
            p = self._v("phx_dm_prediction_result", pred_id)
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
            reasoning_steps, evidence = self._parse_reasoning(r)
            break
        return {"sources": sources, "reasoning_steps": reasoning_steps, "evidence": evidence[:8]}

    # ------------------------------------------------------- households listing

    def households_for_advisor(self, advisor_id: str) -> list[dict]:
        results = run_catalog_query(
            self._graph,
            "get_advisor_book_of_business",
            {"advisor_id": advisor_id, "result_limit": 100000},
        )
        if results is not None:
            entry = _entry(results, "households")
            if entry is not None:
                rows = []
                for row in entry.get("households") or []:
                    a = _attrs(row)
                    hid = str(row.get("v_id"))
                    rows.append({
                        "household_id": hid,
                        "household_name": a.get("household_name", hid),
                        "segment": a.get("segment"),
                        "total_aum": a.get("total_aum"),
                    })
                rows.sort(key=lambda r: float(r.get("total_aum") or 0), reverse=True)
                return rows
            logger.warning(
                "get_advisor_book_of_business returned no households entry for %s — "
                "falling back to local store traversal", advisor_id,
            )
        else:
            logger.warning(
                "get_advisor_book_of_business unavailable for %s — falling back to "
                "local store traversal", advisor_id,
            )
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

    # ------------------------------------------------------------------ helpers

    def _account_detail(self, acc_row: dict) -> tuple[dict, list[dict]]:
        """(account output row, that account's transaction vset rows) via GQ-012;
        holdings/transactions fall back to the store traversal (logged) if the
        query is unavailable."""
        acc_id = str(acc_row.get("v_id"))
        a = _attrs(acc_row)
        holdings: list[dict] = []
        tx_rows: list[dict] = []
        results = run_catalog_query(
            self._graph, "get_account_holdings_and_activity", {"account_id": acc_id}
        )
        entry = _entry(results, "products") if results is not None else None
        if entry is not None:
            for row in entry.get("products") or []:
                p = _attrs(row)
                holdings.append({
                    "product_id": str(row.get("v_id")),
                    "product_name": p.get("product_name"),
                    "risk_level": p.get("risk_level"),
                    "managed": bool(p.get("managed_flag")),
                })
            tx_rows = list(entry.get("transactions") or [])
        else:
            logger.warning(
                "get_account_holdings_and_activity unavailable for %s — falling "
                "back to local store traversal", acc_id,
            )
            store = self._store
            for pid in store.out_ids("phx_dm_account_holds_product", acc_id):
                p = self._v("phx_dm_product", pid)
                holdings.append({
                    "product_id": pid,
                    "product_name": p.get("product_name"),
                    "risk_level": p.get("risk_level"),
                    "managed": bool(p.get("managed_flag")),
                })
            for tx_id in store.in_ids("phx_dm_transaction_for_account", acc_id):
                t = store.vertex("phx_dm_revenue_transaction", tx_id)
                if t is not None:
                    tx_rows.append({"v_id": str(tx_id), "v_type": "phx_dm_revenue_transaction", "attributes": t})
        account = {
            "account_id": acc_id,
            "account_name": a.get("account_name"),
            "account_type": a.get("account_type"),
            "status": a.get("status"),
            "opened_date": a.get("opened_date"),
            "current_value": float(a.get("current_value") or 0),
            "holdings": holdings,
        }
        return account, tx_rows

    def _has_embedding(self, entity_type: str, entity_id: str) -> bool:
        """Whether the entity has a persisted embedding with a parseable vector —
        via GQ-024 get_embeddings_for_entity (same attribute-filter semantics as
        the GSQL query), logged store fallback otherwise."""
        results = run_catalog_query(
            self._graph,
            "get_embeddings_for_entity",
            {"entity_type": entity_type, "entity_id": entity_id},
        )
        if results is not None:
            entry = _entry(results, "embeddings")
            if entry is not None:
                for row in entry.get("embeddings") or []:
                    e = _attrs(row)
                    if str(e.get("entity_type", "")).upper() == entity_type and _parse_vector(e.get("vector_preview")):
                        return True
                return False
            logger.warning(
                "get_embeddings_for_entity returned no embeddings entry for %s/%s — "
                "falling back to local store traversal", entity_type, entity_id,
            )
        else:
            logger.warning(
                "get_embeddings_for_entity unavailable for %s/%s — falling back to "
                "local store traversal", entity_type, entity_id,
            )
        return entity_id in _embeddings_by_entity(self._store, entity_type)

    # ------------------------------------------------------------------ profile

    def profile(self, household_id: str) -> dict:
        results = run_catalog_query(
            self._graph, "get_household_360", {"household_id": household_id}
        )
        entry = _entry(results, "household") if results is not None else None
        if entry is None:
            if results is not None:
                logger.warning(
                    "get_household_360 returned no household entry for %s — "
                    "falling back to local store traversal", household_id,
                )
            else:
                logger.warning(
                    "get_household_360 unavailable for %s — falling back to "
                    "local store traversal", household_id,
                )
            return self._profile_store(household_id)

        hh_rows = entry.get("household") or []
        hh = _attrs(hh_rows[0]) if hh_rows else {}

        advisor_rows = entry.get("advisors") or []
        advisor_ids = [str(r.get("v_id")) for r in advisor_rows]
        advisor = _attrs(advisor_rows[0]) if advisor_rows else {}

        accounts: list[dict] = []
        tx_by_id: dict[str, dict] = {}
        for acc_row in entry.get("accounts") or []:
            account, tx_rows = self._account_detail(acc_row)
            accounts.append(account)
            for row in tx_rows:
                tx_by_id[str(row.get("v_id"))] = _attrs(row)
        accounts.sort(key=lambda r: r["current_value"], reverse=True)

        # recent transactions across the household (household-linked transactions
        # are exactly the union of its accounts' transactions — verified 0/360
        # set mismatches; ordered by transaction id to match the store edge order)
        txns = []
        for tx_id in sorted(tx_by_id):
            t = tx_by_id[tx_id]
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
        for row in entry.get("recommendations") or []:
            r = _attrs(row)
            if r:
                rid = str(row.get("v_id"))
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
        similar = {
            "households": similar_entities("HOUSEHOLD", household_id, 3)
            if self._has_embedding("HOUSEHOLD", household_id) else None,
            "accounts": None,
        }
        top_acct = next(
            (a["account_id"] for a in accounts if self._has_embedding("ACCOUNT", a["account_id"])),
            None,
        )
        if top_acct:
            similar["accounts"] = similar_entities("ACCOUNT", top_acct, 3)

        return self._assemble_profile(household_id, hh, advisor_ids, advisor, accounts, txns, total_revenue, recs, similar)

    @staticmethod
    def _assemble_profile(
        household_id: str, hh: dict, advisor_ids: list[str], advisor: dict,
        accounts: list[dict], txns: list[dict], total_revenue: float,
        recs: list[dict], similar: dict,
    ) -> dict:
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

    def _profile_store(self, household_id: str) -> dict:
        """Logged fallback: the original direct store traversal."""
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

        return self._assemble_profile(household_id, hh, advisor_ids, advisor, accounts, txns, total_revenue, recs, similar)
