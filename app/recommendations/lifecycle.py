"""Section 13 — Recommendation lifecycle (state machine + impact ledger).

The single durable authority for a recommendation's status. The live pipeline
(`RecommendationService.generate_for_advisor`) re-upserts rec vertices with a
transient status on every call, so status CANNOT live authoritatively on the
graph vertex — it lives here in SQLite and is merged back into every read.

Design: docs/design/section13_lifecycle_design.md (fable-architect, §13.7).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.feature_store.sqlite_manager import SQLiteManager
from app.graph.client import get_graph_client
from app.graph.artifacts import upsert_vertex, upsert_edge
from app.graph.queries.common import run_catalog_query, graph_fallback_store
from app.shared.ids import new_id

# The allowed-transition table — the single source of truth for the state machine.
# from_status -> {action: to_status}. Terminal statuses have no entry (all actions 409).
TRANSITIONS: dict[str, dict[str, str]] = {
    "OPEN":        {"accept": "ACCEPTED", "complete": "COMPLETED", "modify": "MODIFIED",
                    "reject": "REJECTED", "ignore": "IGNORED"},
    "ACCEPTED":    {"start": "IN_PROGRESS", "complete": "COMPLETED", "modify": "MODIFIED"},
    "IN_PROGRESS": {"complete": "COMPLETED", "modify": "MODIFIED"},
    "MODIFIED":    {"accept": "ACCEPTED", "reopen": "OPEN"},
    # COMPLETED / REJECTED / IGNORED -> terminal (absent = every action rejected)
}
TERMINAL = {"COMPLETED", "REJECTED", "IGNORED"}
# OPEN-shortcut actions that imply an ACCEPTED transition first (UI exposes them on open cards).
_IMPLIES_ACCEPT = {"complete", "modify"}


def canonical(status: str | None) -> str:
    """Map any stored/legacy status to the canonical UPPERCASE lifecycle state."""
    if not status:
        return "OPEN"
    s = str(status).upper()
    if s in ("PRESENTED", "GENERATED"):
        return "OPEN"
    return s


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LifecycleError(Exception):
    """Illegal transition (maps to HTTP 409)."""


class RecommendationLifecycleService:
    def __init__(self) -> None:
        # Durable state (status, status-transitions, impact ledger) now flows through the
        # StateRepository adapter — TigerGraph authority + SQLite fallback. `self.db` is
        # retained ONLY for the generated-recommendation attribute cache (register_generated /
        # _rec_attrs mirror), which is an operational cache, not one of the migrated durable
        # domains (the authoritative rec attrs come from the graph vertex in _rec_attrs).
        from app.repositories.state_repository import get_state_repository

        self.db = SQLiteManager()
        self.state = get_state_repository()
        self.initialize()

    # ---- schema ------------------------------------------------------------
    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_recommendation (
                    recommendation_id TEXT PRIMARY KEY, entity_type TEXT, entity_id TEXT,
                    household_id TEXT, opportunity_id TEXT, prediction_id TEXT, playbook_id TEXT,
                    recommendation_type TEXT, title TEXT, action_text TEXT, rationale TEXT,
                    score REAL, confidence REAL, status TEXT, compliance_status TEXT,
                    supporting_documents_json TEXT, evidence_json TEXT, reasoning_steps_json TEXT,
                    created_ts TEXT, updated_ts TEXT
                )""")
            # Guarded ALTERs (SQLite has no ADD COLUMN IF NOT EXISTS).
            cols = {r[1] for r in conn.execute("PRAGMA table_info(phx_dm_local_recommendation)")}
            for col, decl in [("advisor_id", "TEXT"), ("action_family", "TEXT"),
                              ("estimated_revenue_impact", "REAL"), ("status_note", "TEXT")]:
                if col not in cols:
                    conn.execute(f"ALTER TABLE phx_dm_local_recommendation ADD COLUMN {col} {decl}")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_phx_dm_recommendation_advisor "
                         "ON phx_dm_local_recommendation(advisor_id, status)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_rec_status_transition (
                    transition_id TEXT PRIMARY KEY, recommendation_id TEXT NOT NULL, advisor_id TEXT,
                    from_status TEXT NOT NULL, to_status TEXT NOT NULL, action TEXT NOT NULL,
                    actor_type TEXT NOT NULL, actor_id TEXT, note TEXT, created_ts TEXT NOT NULL
                )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rec_transition_rec "
                         "ON phx_dm_local_rec_status_transition(recommendation_id, created_ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rec_transition_advisor "
                         "ON phx_dm_local_rec_status_transition(advisor_id, created_ts)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_impact_ledger (
                    ledger_id TEXT PRIMARY KEY, recommendation_id TEXT NOT NULL UNIQUE,
                    advisor_id TEXT NOT NULL, opportunity_id TEXT, action_family TEXT,
                    impact_amount REAL NOT NULL, impact_type TEXT NOT NULL DEFAULT 'REVENUE',
                    source_transaction_id TEXT NOT NULL, note TEXT, created_ts TEXT NOT NULL
                )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_impact_ledger_advisor "
                         "ON phx_dm_local_impact_ledger(advisor_id, created_ts)")
            conn.commit()

    # ---- status reads ------------------------------------------------------
    def effective_status(self, recommendation_id: str) -> str:
        # Graph-authoritative (latest transition), SQLite fallback — via the adapter.
        status = self.state.get_rec_status(recommendation_id)
        return canonical(status) if status else "OPEN"

    def allowed_actions(self, status: str) -> list[str]:
        return list(TRANSITIONS.get(canonical(status), {}).keys())

    def _rec_attrs(self, recommendation_id: str) -> dict:
        """Rec attributes via GQ-029 get_recommendation_detail first (installed query in
        real mode, identical-shape mock in mock mode), SQLite mirror as fallback. The
        rec->advisor edge lookup stays a direct store traversal — no catalog query does
        the reverse recommendation->advisor hop (see migration report)."""
        graph = get_graph_client()
        v: dict = {}
        graph_opp_id = None
        results = run_catalog_query(graph, "get_recommendation_detail",
                                    {"recommendation_id": recommendation_id})
        if results is not None:
            entry = results[0] if results else {}
            recs = entry.get("recommendation") or []
            v = (recs[0].get("attributes", recs[0]) or {}) if recs else {}
            opps = entry.get("opportunities") or []
            if opps:
                graph_opp_id = opps[0].get("v_id")
        else:
            # fallback: original direct store traversal (logged by run_catalog_query)
            store = graph_fallback_store(graph)
            v = store.vertex("phx_dm_recommendation", recommendation_id) or {}
            graph_opp_id = (store.out_ids("phx_dm_recommendation_addresses_opportunity", recommendation_id) or [None])[0]
        # rec -> advisor via GQ-060 get_recommendation_advisor (run_query); the
        # direct store edge read below survives only as the logged fallback.
        advisor = None
        adv_results = run_catalog_query(graph, "get_recommendation_advisor",
                                        {"recommendation_id": recommendation_id})
        if adv_results is not None:
            for entry in adv_results:
                advisors = entry.get("advisor")
                if advisors:
                    advisor = str(advisors[0].get("v_id"))
                    break
        else:
            store = graph_fallback_store(graph)
            ids = store.in_ids("phx_dm_recommendation_for_advisor", recommendation_id)  # to-advisor
            if not ids:
                ids = store.out_ids("phx_dm_recommendation_for_advisor", recommendation_id)
            if ids:
                advisor = ids[0]
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT advisor_id, action_family, estimated_revenue_impact, opportunity_id, title "
                "FROM phx_dm_local_recommendation WHERE recommendation_id=?", (recommendation_id,)).fetchone()
        mirror = dict(zip(["advisor_id", "action_family", "estimated_revenue_impact", "opportunity_id", "title"], row)) if row else {}
        return {
            "advisor_id": advisor or mirror.get("advisor_id"),
            "title": v.get("title") or mirror.get("title") or recommendation_id,
            "estimated_revenue_impact": float(v.get("estimated_revenue_impact")
                                              if v.get("estimated_revenue_impact") is not None
                                              else (mirror.get("estimated_revenue_impact") or 0.0)),
            "action_family": v.get("recommendation_type") or mirror.get("action_family"),
            "opportunity_id": mirror.get("opportunity_id") or graph_opp_id,
        }

    # ---- mirror upsert (status-preserving) --------------------------------
    def register_generated(self, rec: dict, advisor_id: str) -> dict:
        """Upsert the SQLite mirror for a freshly-generated rec WITHOUT clobbering
        an existing lifecycle status. Returns merged {status, status_note, allowed_actions}."""
        rid = rec["recommendation_id"]
        with self.db.connect() as conn:
            existing = conn.execute("SELECT status, status_note FROM phx_dm_local_recommendation "
                                    "WHERE recommendation_id=?", (rid,)).fetchone()
            status = canonical(existing[0]) if existing else "OPEN"
            status_note = existing[1] if existing else None
            conn.execute("""
                INSERT INTO phx_dm_local_recommendation
                    (recommendation_id, entity_type, entity_id, advisor_id, opportunity_id,
                     prediction_id, playbook_id, recommendation_type, title, action_text,
                     action_family, score, confidence, estimated_revenue_impact, status,
                     status_note, created_ts, updated_ts)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(recommendation_id) DO UPDATE SET
                    advisor_id=excluded.advisor_id, opportunity_id=excluded.opportunity_id,
                    prediction_id=excluded.prediction_id, playbook_id=excluded.playbook_id,
                    recommendation_type=excluded.recommendation_type, title=excluded.title,
                    action_text=excluded.action_text, action_family=excluded.action_family,
                    score=excluded.score, confidence=excluded.confidence,
                    estimated_revenue_impact=excluded.estimated_revenue_impact,
                    updated_ts=excluded.updated_ts
                    -- NB: status / status_note deliberately NOT overwritten (preserve lifecycle)
            """, (rid, "ADVISOR", advisor_id, advisor_id, rec.get("opportunity_id"),
                  rec.get("prediction_id"), rec.get("playbook_id"), rec.get("recommendation_type"),
                  rec.get("title"), rec.get("action_text"), rec.get("recommendation_type"),
                  rec.get("priority_score"), rec.get("confidence"), rec.get("estimated_revenue_impact"),
                  status, status_note, _now(), _now()))
            conn.commit()
        return {"status": status, "status_note": status_note,
                "allowed_actions": self.allowed_actions(status), "terminal": status in TERMINAL}

    # ---- the transition choke point ---------------------------------------
    def apply_action(self, recommendation_id: str, action: str, actor_type: str = "advisor",
                     actor_id: str | None = None, note: str | None = None) -> dict:
        action = action.lower()
        current = self.effective_status(recommendation_id)
        if current in TERMINAL or action not in TRANSITIONS.get(current, {}):
            raise LifecycleError(f"{current} does not allow action '{action}' for {recommendation_id}")

        attrs = self._rec_attrs(recommendation_id)
        advisor_id = attrs["advisor_id"]
        transitions: list[tuple[str, str, str]] = []  # (from, to, action)

        # OPEN-shortcut: record the implied accept first so the audit trail is spec-formal.
        if current == "OPEN" and action in _IMPLIES_ACCEPT:
            transitions.append(("OPEN", "ACCEPTED", "accept"))
            frm = "ACCEPTED"
        else:
            frm = current
        to = TRANSITIONS[frm][action]
        transitions.append((frm, to, action))

        impact = None
        # Status-transition audit trail + status → the StateRepository adapter (graph vertices
        # via phx_dm_rec_status_transition + status on the recommendation vertex; SQLite fallback).
        for (f, t, a) in transitions:
            self.state.record_transition({
                "transition_id": new_id("TRN"), "recommendation_id": recommendation_id,
                "advisor_id": advisor_id, "from_status": f, "to_status": t, "action": a,
                "actor_type": actor_type, "actor_id": actor_id,
                "note": note if a == action else None, "created_ts": _now()})
        self.state.set_rec_status(recommendation_id, to)

        status_note = None
        if to == "COMPLETED":
            impact = self._generate_impact(recommendation_id, attrs, actor_type, actor_id, note)
            status_note = impact["note"]
            self.state.set_rec_status(recommendation_id, to, note=status_note)

        return {"recommendation_id": recommendation_id, "from_status": current, "to_status": to,
                "transition_id": transitions[-1] and new_id("TRN"), "status_note": status_note,
                "allowed_actions": self.allowed_actions(to), "terminal": to in TERMINAL, "impact": impact}

    # ---- impact generation (completion) -----------------------------------
    def _generate_impact(self, recommendation_id: str, attrs: dict, actor_type: str,
                         actor_id: str | None, note: str | None) -> dict:
        advisor_id = attrs["advisor_id"]
        impact_amount = round(float(attrs["estimated_revenue_impact"] or 0.0), 2)
        tx_id = f"TXIMP_{recommendation_id}"
        graph = get_graph_client()

        # Inject the synthetic revenue transaction + edges (idempotent via deterministic tx_id).
        upsert_vertex(graph, "phx_dm_revenue_transaction", "transaction_id", {
            "transaction_id": tx_id, "transaction_date": "2026-06-30",
            "revenue_amount": impact_amount, "transaction_type": "RECOMMENDATION_IMPACT",
            "quantity": 0, "gross_amount": impact_amount, "source_system": "IPERFORM_LIFECYCLE",
        })
        if advisor_id:
            upsert_edge(graph, "phx_dm_transaction_for_advisor", "phx_dm_revenue_transaction",
                        "phx_dm_advisor", tx_id, advisor_id)
        upsert_edge(graph, "phx_dm_transaction_from_recommendation", "phx_dm_revenue_transaction",
                    "phx_dm_recommendation", tx_id, recommendation_id)

        note_text = (f"Completed {datetime.now(timezone.utc).date().isoformat()} by {actor_type} "
                     f"{actor_id or ''}: {attrs['title']} — +${impact_amount:,.0f} revenue impact recorded "
                     f"(transaction {tx_id}).{(' ' + note) if note else ''}")

        # Impact-ledger entry → the StateRepository adapter (phx_dm_impact_ledger vertex +
        # impact_for_advisor / impact_from_recommendation edges in the graph; SQLite fallback).
        self.state.add_impact_entry({
            "ledger_id": new_id("LEDG"), "recommendation_id": recommendation_id, "advisor_id": advisor_id,
            "opportunity_id": attrs.get("opportunity_id"), "action_family": attrs.get("action_family"),
            "impact_amount": impact_amount, "impact_type": "REVENUE", "source_transaction_id": tx_id,
            "note": note_text, "created_ts": _now()})

        # Mark the opportunity ADDRESSED (additive merge).
        if attrs.get("opportunity_id"):
            try:
                upsert_vertex(graph, "phx_dm_opportunity", "opportunity_id",
                              {"opportunity_id": attrs["opportunity_id"], "status": "ADDRESSED",
                               "addressed_by_recommendation_id": recommendation_id})
            except Exception:
                pass

        # Recompute + persist the ONE advisor's feature snapshot so snapshot-based
        # screens (Advisor 360 KPIs, Exec rollup) reflect the impact.
        if advisor_id:
            try:
                from app.features.engineering import FeatureEngineeringService
                from app.features.snapshot_store import SnapshotStore
                snap = FeatureEngineeringService().compute_advisor_snapshot(advisor_id)
                SnapshotStore().save(snap)
            except Exception:
                pass

        # Memory write (second independent route for 13.4).
        try:
            from app.services.memory_service import MemoryService
            from app.models.memory import ContextMemoryCreateRequest, MemoryScopeType, MemoryType
            MemoryService().create_memory(ContextMemoryCreateRequest(
                memory_type=MemoryType.FEEDBACK, scope_type=MemoryScopeType.ADVISOR,
                scope_id=advisor_id, title=f"Completed recommendation {recommendation_id}",
                summary=note_text,
                facts={"recommendation_id": recommendation_id, "to_status": "COMPLETED",
                       "impact_amount": impact_amount, "source_transaction_id": tx_id},
                confidence=0.9, source="recommendation_lifecycle"), write_to_graph=False)
        except Exception:
            pass

        # PROCEDURAL memory (previously unpopulated) — a completed action that worked is
        # reusable "how to act" knowledge. Written organically through the StateRepository
        # adapter, so procedural memory now lives in the graph like the other memory types.
        try:
            from app.services.memory_service import MemoryService
            from app.models.memory import ContextMemoryCreateRequest, MemoryScopeType, MemoryType
            family = attrs.get("action_family") or "GENERAL"
            MemoryService().create_memory(ContextMemoryCreateRequest(
                memory_type=MemoryType.PROCEDURAL, scope_type=MemoryScopeType.ADVISOR,
                scope_id=advisor_id,
                title=f"Proven play: {family}",
                summary=(f"For {family} situations, completing \"{attrs['title']}\" produced a measured "
                         f"+${impact_amount:,.0f} revenue impact — a proven action to repeat when this "
                         f"pattern recurs."),
                facts={"action_family": family, "recommendation_id": recommendation_id,
                       "impact_amount": impact_amount, "play": "repeat_on_similar_pattern"},
                confidence=0.85, source="recommendation_lifecycle_procedural"))
        except Exception:
            pass

        return {"ledger_id": None, "impact_amount": impact_amount, "impact_type": "REVENUE",
                "source_transaction_id": tx_id, "note": note_text, "opportunity_id": attrs.get("opportunity_id")}

    # ---- reads for the UI / context / regeneration ------------------------
    def lifecycle_for(self, recommendation_id: str) -> dict:
        status = self.effective_status(recommendation_id)
        # transitions + impact via graph traversal through the adapter.
        trns = self.state.transitions_for(recommendation_id)
        led = self.state.impact_entry_for_recommendation(recommendation_id)
        status_note = (led or {}).get("note")
        return {
            "recommendation_id": recommendation_id, "status": status,
            "status_note": status_note,
            "allowed_actions": self.allowed_actions(status), "terminal": status in TERMINAL,
            "transitions": [{k: t.get(k) for k in ["from_status", "to_status", "action", "actor_type", "actor_id", "note", "created_ts"]} for t in trns],
            "impact": ({k: led.get(k) for k in ["ledger_id", "impact_amount", "source_transaction_id", "note", "created_ts"]} if led else None),
            "reasoning_trace_id": f"REASON_{recommendation_id}",
        }

    def addressed_opportunity_ids(self, advisor_id: str) -> set[str]:
        return {e["opportunity_id"] for e in self.state.impact_entries_for_advisor(advisor_id)
                if e.get("opportunity_id")}

    def ledger_for_opportunity(self, opportunity_id: str) -> dict | None:
        entries = [e for e in self.state.all_impact_entries() if e.get("opportunity_id") == opportunity_id]
        entries.sort(key=lambda e: str(e.get("created_ts") or ""), reverse=True)
        if not entries:
            return None
        e = entries[0]
        return {"recommendation_id": e.get("recommendation_id"), "created_ts": e.get("created_ts"), "note": e.get("note")}

    def counts_for_advisor(self, advisor_id: str) -> dict:
        """Status counts across the advisor's recommendations — derived from the graph rec
        vertices' status attribute (set via the adapter), with the SQLite mirror as fallback."""
        counts = {k: 0 for k in ["open", "accepted", "in_progress", "completed", "rejected", "ignored", "modified"]}
        graph = get_graph_client()
        seen = False
        results = run_catalog_query(graph, "get_recommendations",
                                    {"target_type": "ADVISOR", "target_id": advisor_id})
        if results is not None:
            for entry in results:
                for row in entry.get("recommendations") or []:
                    st = (row.get("attributes", row) or {}).get("status")
                    if st:
                        seen = True
                        key = canonical(st).lower()
                        counts[key] = counts.get(key, 0) + 1
        else:
            # fallback: original direct store traversal (logged by run_catalog_query)
            store = graph_fallback_store(graph)
            rec_ids = store.in_ids("phx_dm_recommendation_for_advisor", advisor_id) or \
                store.out_ids("phx_dm_recommendation_for_advisor", advisor_id)
            for rid in rec_ids:
                st = (store.vertex("phx_dm_recommendation", rid) or {}).get("status")
                if st:
                    seen = True
                    key = canonical(st).lower()
                    counts[key] = counts.get(key, 0) + 1
        if not seen:  # fallback to the SQLite rec-attr cache
            with self.db.connect() as conn:
                for status, n in conn.execute("SELECT status, COUNT(*) FROM phx_dm_local_recommendation "
                                              "WHERE advisor_id=? GROUP BY status", (advisor_id,)):
                    counts[canonical(status).lower()] = counts.get(canonical(status).lower(), 0) + n
        return counts

    def recent_activity_for_advisor(self, advisor_id: str, limit: int = 5) -> dict:
        # Impact history from the graph (traversal); rec titles/status via GQ-028
        # get_recommendations (one call for the advisor's recs), store vertex as fallback.
        entries = self.state.impact_entries_for_advisor(advisor_id)
        graph = get_graph_client()
        rec_attrs_map: dict[str, dict] | None = None
        results = run_catalog_query(graph, "get_recommendations",
                                    {"target_type": "ADVISOR", "target_id": advisor_id})
        if results is not None:
            rec_attrs_map = {}
            for entry in results:
                for row in entry.get("recommendations") or []:
                    rec_attrs_map[str(row.get("v_id"))] = row.get("attributes", row) or {}
        # fallback store used only when the query path returned None (logged already)
        store = graph_fallback_store(graph)
        events = []
        for e in entries[:limit]:
            rid = e.get("recommendation_id")
            if rec_attrs_map is not None:
                v = rec_attrs_map.get(str(rid), {})
            else:
                v = store.vertex("phx_dm_recommendation", rid) or {}
            events.append({
                "recommendation_id": rid, "title": v.get("title") or e.get("note") or rid,
                "status": canonical(v.get("status") or "COMPLETED"), "note": e.get("note"),
                "created_ts": e.get("created_ts") or "",
                "impact_amount": e.get("impact_amount"), "source_transaction_id": e.get("source_transaction_id")})
        total = sum(float(e.get("impact_amount") or 0.0) for e in entries)
        ledger_ids = [e.get("ledger_id") for e in entries]
        return {"events": events, "total_impact": float(total), "ledger_ids": ledger_ids}

    # ---- ledger reads (for the Impact Ledger page) ------------------------
    def _advisor_name(self, advisor_id: str) -> str:
        graph = get_graph_client()
        results = run_catalog_query(graph, "get_advisor_360", {"advisor_id": str(advisor_id)})
        if results is not None:
            for entry in results:
                for row in entry.get("advisor") or []:
                    name = (row.get("attributes", row) or {}).get("advisor_name")
                    if name:
                        return str(name)
            return str(advisor_id)
        # fallback: original direct store read (logged by run_catalog_query)
        v = graph_fallback_store(graph).vertex("phx_dm_advisor", advisor_id) or {}
        return str(v.get("advisor_name") or advisor_id)

    def _rec_title(self, recommendation_id: str) -> str:
        graph = get_graph_client()
        results = run_catalog_query(graph, "get_recommendation_detail",
                                    {"recommendation_id": str(recommendation_id)})
        if results is not None:
            entry = results[0] if results else {}
            recs = entry.get("recommendation") or []
            v = (recs[0].get("attributes", recs[0]) or {}) if recs else {}
        else:
            # fallback: original direct store read (logged by run_catalog_query)
            v = graph_fallback_store(graph).vertex("phx_dm_recommendation", recommendation_id) or {}
        if v.get("title"):
            return str(v["title"])
        with self.db.connect() as conn:
            row = conn.execute("SELECT title FROM phx_dm_local_recommendation WHERE recommendation_id=?",
                               (recommendation_id,)).fetchone()
        return (row[0] if row and row[0] else recommendation_id)

    def ledger_entries(self, advisor_id: str | None = None) -> list[dict]:
        # Impact ledger via the adapter (graph traversal; SQLite fallback), enriched with names.
        entries = (self.state.impact_entries_for_advisor(advisor_id) if advisor_id
                   else self.state.all_impact_entries())
        out = []
        for e in entries:
            e = dict(e)
            e["advisor_name"] = self._advisor_name(e.get("advisor_id"))
            e["recommendation_title"] = self._rec_title(e.get("recommendation_id"))
            out.append(e)
        return out

    def lifecycle_totals(self) -> dict:
        """Per-status recommendation counts across ALL advisors — for real
        acceptance/completion rates on the Business Impact page (13B.4). Served by
        GQ-061 get_recommendation_status_counts (direct vertex-set aggregation —
        GQ-041 scope=ALL misses the 60 household-level REC_HH_* recs); the store
        scan below survives only as the logged fallback, SQLite mirror after that."""
        counts = {k: 0 for k in ["open", "accepted", "in_progress", "completed", "rejected", "ignored", "modified"]}
        seen = False
        results = run_catalog_query(get_graph_client(), "get_recommendation_status_counts", {})
        status_map: dict | None = None
        if results is not None:
            for entry in results:
                if entry.get("status_counts") is not None:
                    status_map = entry["status_counts"]
                    break
        if status_map is not None:
            for st, n in status_map.items():
                if st:
                    seen = True
                    key = canonical(st).lower()
                    counts[key] = counts.get(key, 0) + int(n)
        else:
            store = graph_fallback_store(get_graph_client())
            for attrs in store.all_vertices("phx_dm_recommendation").values():
                st = attrs.get("status")
                if st:
                    seen = True
                    key = canonical(st).lower()
                    counts[key] = counts.get(key, 0) + 1
        if not seen:
            with self.db.connect() as conn:
                for status, n in conn.execute("SELECT status, COUNT(*) FROM phx_dm_local_recommendation GROUP BY status"):
                    counts[canonical(status).lower()] = counts.get(canonical(status).lower(), 0) + n
        return counts

    def ledger_totals(self, entries: list[dict]) -> dict:
        by_family: dict[str, float] = {}
        by_advisor: dict[str, float] = {}
        for e in entries:
            by_family[e["action_family"] or "OTHER"] = by_family.get(e["action_family"] or "OTHER", 0.0) + e["impact_amount"]
            by_advisor[e["advisor_id"]] = by_advisor.get(e["advisor_id"], 0.0) + e["impact_amount"]
        return {
            "total_impact": round(sum(e["impact_amount"] for e in entries), 2),
            "completed_count": len(entries),
            "advisors_affected": len(by_advisor),
            "latest": entries[0] if entries else None,
            "by_family": {k: round(v, 2) for k, v in sorted(by_family.items(), key=lambda x: -x[1])},
            "by_advisor": sorted(({"advisor_id": k, "advisor_name": self._advisor_name(k), "impact": round(v, 2)}
                                  for k, v in by_advisor.items()), key=lambda x: -x["impact"]),
            "lifecycle_totals": self.lifecycle_totals(),
        }

    _last_replay: dict = {"ledger_entries_replayed": 0, "statuses_reapplied": 0}

    # ---- Story-Mode reset (13B.2) — same-process replayability -------------
    def reset_advisor(self, advisor_id: str) -> dict:
        """Reset an advisor's lifecycle to pristine (for replayable Story Mode): delete
        lifecycle/transition/ledger rows + lifecycle memories, remove the injected TXIMP_
        transactions from the in-memory store (no restart needed), un-address opportunities,
        and recompute the base snapshot. REFUSES anchored advisors (A001/A020)."""
        ANCHORED = {"A001", "A020"}
        if advisor_id in ANCHORED:
            raise LifecycleError(f"{advisor_id} is an anchored verification advisor — refusing to reset (Section 13 guardrail).")
        graph = get_graph_client()
        # read ledger entries via the adapter (graph authority) — need tx + opportunity ids first.
        entries = self.state.impact_entries_for_advisor(advisor_id)
        tx_removed = 0
        for e in entries:
            tx_id, opp_id = e.get("source_transaction_id"), e.get("opportunity_id")
            if tx_id and str(tx_id).startswith("TXIMP_"):
                if graph.store.remove_vertex("phx_dm_revenue_transaction", tx_id):
                    tx_removed += 1
            # remove the graph impact-ledger vertex + its edges (graph is authority now)
            if e.get("ledger_id"):
                graph.store.remove_vertex("phx_dm_impact_ledger", e["ledger_id"])
            if opp_id:  # un-address so regeneration re-issues the rec
                try:
                    upsert_vertex(graph, "phx_dm_opportunity", "opportunity_id",
                                  {"opportunity_id": opp_id, "status": "OPEN", "addressed_by_recommendation_id": ""})
                except Exception:
                    pass
        n_led = len(entries)
        # clear the graph status-transition vertices + reset rec statuses for this advisor
        for tid in [t for t, a in graph.store.all_vertices("phx_dm_rec_status_transition").items()
                    if a.get("advisor_id") == advisor_id]:
            graph.store.remove_vertex("phx_dm_rec_status_transition", tid)
        rec_ids = graph.store.in_ids("phx_dm_recommendation_for_advisor", advisor_id) or \
            graph.store.out_ids("phx_dm_recommendation_for_advisor", advisor_id)
        for rid in rec_ids:
            if (graph.store.vertex("phx_dm_recommendation", rid) or {}).get("status") not in (None, "OPEN"):
                upsert_vertex(graph, "phx_dm_recommendation", "recommendation_id",
                              {"recommendation_id": rid, "status": "OPEN", "status_note": ""})
        # clear the SQLite fallback tier's rows too (reset means both stores)
        with self.db.connect() as conn:
            for t in ["phx_dm_local_recommendation", "phx_dm_local_rec_status_transition", "phx_dm_local_impact_ledger"]:
                conn.execute(f"DELETE FROM {t} WHERE advisor_id=?", (advisor_id,))
            conn.execute("DELETE FROM phx_dm_local_context_memory WHERE scope_id=? AND source='recommendation_lifecycle'", (advisor_id,))
            conn.commit()
        # recompute base snapshot (store no longer has the injected tx)
        base_rev = None
        try:
            from app.features.engineering import FeatureEngineeringService
            from app.features.snapshot_store import SnapshotStore
            snap = FeatureEngineeringService().compute_advisor_snapshot(advisor_id)
            SnapshotStore().save(snap)
            base_rev = snap.values().get("revenue_ltm")
        except Exception:
            pass
        return {"advisor_id": advisor_id, "ledger_entries_removed": n_led,
                "transactions_removed": tx_removed, "snapshot_revenue_ltm": base_rev,
                "note": "Learning history (bandit weights / GNN) is intentionally NOT rewound — it is cumulative."}

    # ---- boot replay / graph rehydration ----------------------------------
    def replay_on_boot(self) -> dict:
        """Rehydrate the graph from the DURABLE state on boot. In mock mode the graph store is
        in-memory (rebuilt from CSVs each boot), so runtime-written impact/transition/status
        vertices are gone after a restart — but the SQLite fallback tier persisted them. We read
        the durable entries via the adapter (graph-primary; after a restart that's empty, so the
        fallback returns the SQLite rows) and re-write them back into the graph so graph-based
        reads reflect the full history again. This is the SQLite safety-net doing its job."""
        graph = get_graph_client()
        entries = self.state.all_impact_entries()
        replayed = 0
        statuses = 0
        for e in entries:
            tx_id = e.get("source_transaction_id")
            rid = e.get("recommendation_id")
            advisor_id = e.get("advisor_id")
            amount = float(e.get("impact_amount") or 0.0)
            try:
                if tx_id:
                    upsert_vertex(graph, "phx_dm_revenue_transaction", "transaction_id", {
                        "transaction_id": tx_id, "transaction_date": "2026-06-30",
                        "revenue_amount": amount, "transaction_type": "RECOMMENDATION_IMPACT",
                        "quantity": 0, "gross_amount": amount, "source_system": "IPERFORM_LIFECYCLE"})
                    if advisor_id:
                        upsert_edge(graph, "phx_dm_transaction_for_advisor", "phx_dm_revenue_transaction",
                                    "phx_dm_advisor", tx_id, advisor_id)
                    if rid:
                        upsert_edge(graph, "phx_dm_transaction_from_recommendation", "phx_dm_revenue_transaction",
                                    "phx_dm_recommendation", tx_id, rid)
                # Rehydrate the impact-ledger vertex + edges into the graph too.
                self.state.add_impact_entry(e)
                # Reapply the completed status onto the rec vertex.
                if rid:
                    self.state.set_rec_status(rid, "COMPLETED")
                    statuses += 1
                replayed += 1
            except Exception:
                pass
        report = {"ledger_entries_replayed": replayed, "statuses_reapplied": statuses}
        RecommendationLifecycleService._last_replay = report
        return report
