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
        self.db = SQLiteManager()
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
        with self.db.connect() as conn:
            row = conn.execute("SELECT status FROM phx_dm_local_recommendation WHERE recommendation_id=?",
                               (recommendation_id,)).fetchone()
        return canonical(row[0]) if row else "OPEN"

    def allowed_actions(self, status: str) -> list[str]:
        return list(TRANSITIONS.get(canonical(status), {}).keys())

    def _rec_attrs(self, recommendation_id: str) -> dict:
        """Rec attributes from the graph vertex first, SQLite mirror as fallback."""
        store = get_graph_client().store
        v = store.vertex("phx_dm_recommendation", recommendation_id) or {}
        advisor = None
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
            "opportunity_id": mirror.get("opportunity_id")
                              or (store.out_ids("phx_dm_recommendation_addresses_opportunity", recommendation_id) or [None])[0],
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
        with self.db.connect() as conn:
            for (f, t, a) in transitions:
                conn.execute("""INSERT INTO phx_dm_local_rec_status_transition
                    (transition_id, recommendation_id, advisor_id, from_status, to_status, action,
                     actor_type, actor_id, note, created_ts) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (new_id("TRN"), recommendation_id, advisor_id, f, t, a, actor_type, actor_id,
                     note if a == action else None, _now()))
            conn.execute("UPDATE phx_dm_local_recommendation SET status=?, updated_ts=? WHERE recommendation_id=?",
                         (to, _now(), recommendation_id))
            conn.commit()

        # Reflect status onto the graph vertex (merge-upsert, additive).
        try:
            upsert_vertex(get_graph_client(), "phx_dm_recommendation", "recommendation_id",
                          {"recommendation_id": recommendation_id, "status": to})
        except Exception:
            pass

        status_note = None
        if to == "COMPLETED":
            impact = self._generate_impact(recommendation_id, attrs, actor_type, actor_id, note)
            status_note = impact["note"]
            with self.db.connect() as conn:
                conn.execute("UPDATE phx_dm_local_recommendation SET status_note=? WHERE recommendation_id=?",
                             (status_note, recommendation_id))
                conn.commit()

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

        with self.db.connect() as conn:
            conn.execute("""INSERT OR REPLACE INTO phx_dm_local_impact_ledger
                (ledger_id, recommendation_id, advisor_id, opportunity_id, action_family,
                 impact_amount, impact_type, source_transaction_id, note, created_ts)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (new_id("LEDG"), recommendation_id, advisor_id, attrs.get("opportunity_id"),
                 attrs.get("action_family"), impact_amount, "REVENUE", tx_id, note_text, _now()))
            conn.commit()

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

        return {"ledger_id": None, "impact_amount": impact_amount, "impact_type": "REVENUE",
                "source_transaction_id": tx_id, "note": note_text, "opportunity_id": attrs.get("opportunity_id")}

    # ---- reads for the UI / context / regeneration ------------------------
    def lifecycle_for(self, recommendation_id: str) -> dict:
        status = self.effective_status(recommendation_id)
        with self.db.connect() as conn:
            note = conn.execute("SELECT status_note FROM phx_dm_local_recommendation WHERE recommendation_id=?",
                                (recommendation_id,)).fetchone()
            trns = conn.execute("""SELECT from_status, to_status, action, actor_type, actor_id, note, created_ts
                FROM phx_dm_local_rec_status_transition WHERE recommendation_id=? ORDER BY created_ts""",
                (recommendation_id,)).fetchall()
            led = conn.execute("""SELECT ledger_id, impact_amount, source_transaction_id, note, created_ts
                FROM phx_dm_local_impact_ledger WHERE recommendation_id=?""", (recommendation_id,)).fetchone()
        return {
            "recommendation_id": recommendation_id, "status": status,
            "status_note": note[0] if note else None,
            "allowed_actions": self.allowed_actions(status), "terminal": status in TERMINAL,
            "transitions": [dict(zip(["from_status", "to_status", "action", "actor_type", "actor_id", "note", "created_ts"], t)) for t in trns],
            "impact": (dict(zip(["ledger_id", "impact_amount", "source_transaction_id", "note", "created_ts"], led)) if led else None),
            "reasoning_trace_id": f"REASON_{recommendation_id}",
        }

    def addressed_opportunity_ids(self, advisor_id: str) -> set[str]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT opportunity_id FROM phx_dm_local_impact_ledger "
                                "WHERE advisor_id=? AND opportunity_id IS NOT NULL", (advisor_id,)).fetchall()
        return {r[0] for r in rows}

    def ledger_for_opportunity(self, opportunity_id: str) -> dict | None:
        with self.db.connect() as conn:
            row = conn.execute("""SELECT recommendation_id, created_ts, note FROM phx_dm_local_impact_ledger
                WHERE opportunity_id=? ORDER BY created_ts DESC LIMIT 1""", (opportunity_id,)).fetchone()
        return {"recommendation_id": row[0], "created_ts": row[1], "note": row[2]} if row else None

    def counts_for_advisor(self, advisor_id: str) -> dict:
        counts = {k: 0 for k in ["open", "accepted", "in_progress", "completed", "rejected", "ignored", "modified"]}
        with self.db.connect() as conn:
            for status, n in conn.execute("SELECT status, COUNT(*) FROM phx_dm_local_recommendation "
                                          "WHERE advisor_id=? GROUP BY status", (advisor_id,)):
                counts[canonical(status).lower()] = counts.get(canonical(status).lower(), 0) + n
        return counts

    def recent_activity_for_advisor(self, advisor_id: str, limit: int = 5) -> dict:
        with self.db.connect() as conn:
            recs = conn.execute("""SELECT r.recommendation_id, r.title, r.status, r.status_note, r.updated_ts,
                    l.impact_amount, l.source_transaction_id
                FROM phx_dm_local_recommendation r
                LEFT JOIN phx_dm_local_impact_ledger l ON l.recommendation_id = r.recommendation_id
                WHERE r.advisor_id=? AND UPPER(r.status) NOT IN ('OPEN','GENERATED','PRESENTED')
                ORDER BY r.updated_ts DESC LIMIT ?""", (advisor_id, limit)).fetchall()
            total = conn.execute("SELECT COALESCE(SUM(impact_amount),0) FROM phx_dm_local_impact_ledger WHERE advisor_id=?",
                                 (advisor_id,)).fetchone()[0]
            ledger_ids = [r[0] for r in conn.execute("SELECT ledger_id FROM phx_dm_local_impact_ledger WHERE advisor_id=?", (advisor_id,))]
        events = [{"recommendation_id": r[0], "title": r[1], "status": canonical(r[2]), "note": r[3],
                   "created_ts": r[4] or "", "impact_amount": r[5], "source_transaction_id": r[6]} for r in recs]
        return {"events": events, "total_impact": float(total or 0.0), "ledger_ids": ledger_ids}

    # ---- ledger reads (for the Impact Ledger page) ------------------------
    def _advisor_name(self, advisor_id: str) -> str:
        v = get_graph_client().store.vertex("phx_dm_advisor", advisor_id) or {}
        return str(v.get("advisor_name") or advisor_id)

    def _rec_title(self, recommendation_id: str) -> str:
        v = get_graph_client().store.vertex("phx_dm_recommendation", recommendation_id) or {}
        if v.get("title"):
            return str(v["title"])
        with self.db.connect() as conn:
            row = conn.execute("SELECT title FROM phx_dm_local_recommendation WHERE recommendation_id=?",
                               (recommendation_id,)).fetchone()
        return (row[0] if row and row[0] else recommendation_id)

    def ledger_entries(self, advisor_id: str | None = None) -> list[dict]:
        sql = ("SELECT ledger_id, recommendation_id, advisor_id, opportunity_id, action_family, "
               "impact_amount, impact_type, source_transaction_id, note, created_ts "
               "FROM phx_dm_local_impact_ledger")
        params: list = []
        if advisor_id:
            sql += " WHERE advisor_id=?"
            params.append(advisor_id)
        sql += " ORDER BY created_ts DESC"
        cols = ["ledger_id", "recommendation_id", "advisor_id", "opportunity_id", "action_family",
                "impact_amount", "impact_type", "source_transaction_id", "note", "created_ts"]
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        out = []
        for r in rows:
            e = dict(zip(cols, r))
            e["advisor_name"] = self._advisor_name(e["advisor_id"])
            e["recommendation_title"] = self._rec_title(e["recommendation_id"])
            out.append(e)
        return out

    def lifecycle_totals(self) -> dict:
        """Per-status recommendation counts across ALL advisors — for real
        acceptance/completion rates on the Business Impact page (13B.4)."""
        counts = {k: 0 for k in ["open", "accepted", "in_progress", "completed", "rejected", "ignored", "modified"]}
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
        # read ledger rows first (need the tx ids + opportunity ids before deleting)
        with self.db.connect() as conn:
            rows = conn.execute("SELECT source_transaction_id, opportunity_id FROM phx_dm_local_impact_ledger WHERE advisor_id=?", (advisor_id,)).fetchall()
        tx_removed = 0
        for tx_id, opp_id in rows:
            if tx_id and str(tx_id).startswith("TXIMP_"):
                assert str(tx_id).startswith("TXIMP_")  # structural safety: never seed data
                if graph.store.remove_vertex("phx_dm_revenue_transaction", tx_id):
                    tx_removed += 1
            if opp_id:  # un-address so regeneration re-issues the rec
                try:
                    upsert_vertex(graph, "phx_dm_opportunity", "opportunity_id",
                                  {"opportunity_id": opp_id, "status": "OPEN", "addressed_by_recommendation_id": ""})
                except Exception:
                    pass
        with self.db.connect() as conn:
            n_led = conn.execute("SELECT COUNT(*) FROM phx_dm_local_impact_ledger WHERE advisor_id=?", (advisor_id,)).fetchone()[0]
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

    # ---- boot replay -------------------------------------------------------
    def replay_on_boot(self) -> dict:
        graph = get_graph_client()
        replayed = 0
        with self.db.connect() as conn:
            ledger = conn.execute("""SELECT recommendation_id, advisor_id, impact_amount, source_transaction_id
                FROM phx_dm_local_impact_ledger""").fetchall()
        for rid, advisor_id, amount, tx_id in ledger:
            try:
                upsert_vertex(graph, "phx_dm_revenue_transaction", "transaction_id", {
                    "transaction_id": tx_id, "transaction_date": "2026-06-30",
                    "revenue_amount": float(amount), "transaction_type": "RECOMMENDATION_IMPACT",
                    "quantity": 0, "gross_amount": float(amount), "source_system": "IPERFORM_LIFECYCLE"})
                if advisor_id:
                    upsert_edge(graph, "phx_dm_transaction_for_advisor", "phx_dm_revenue_transaction",
                                "phx_dm_advisor", tx_id, advisor_id)
                upsert_edge(graph, "phx_dm_transaction_from_recommendation", "phx_dm_revenue_transaction",
                            "phx_dm_recommendation", tx_id, rid)
                replayed += 1
            except Exception:
                pass
        report = {"ledger_entries_replayed": replayed, "statuses_reapplied": 0}
        RecommendationLifecycleService._last_replay = report
        return report
