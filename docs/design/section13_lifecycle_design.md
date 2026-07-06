# Section 13 Design — End-to-End Stateful Recommendation Lifecycle

Author: fable-architect (Section 13.7 delegation). Date: 2026-07-06.
Status: APPROVED DESIGN — implementable as-written by the main (Opus) thread.

Every path, method, and column below was verified against the actual codebase before being
referenced (files read: `app/recommendations/service.py`, `recommendation_repository.py`,
`app/models/recommendations.py`, `app/feedback/service.py`, `app/services/feedback_learning_service.py`,
`app/graph/foundation_store.py`, `app/graph/client.py`, `app/graph/artifacts.py`,
`app/graph/queries/common.py`, `app/revenue/analytics.py`, `app/scope/rollup.py`,
`app/api/routers/advisor360.py`, `app/api/routers/recommendations.py`,
`app/api/routers/feedback_learning.py`, `app/ai/insights/insight_data_collector.py`,
`app/ai/chat/context_assembler.py`, `app/features/snapshot_store.py`, `app/features/engineering.py`,
`app/api/main.py`, `frontend/components/recommendations/recommendations-workspace.tsx`,
`frontend/lib/navigation.ts`).

---

## 0. Ground truth this design is built on (verified facts, not assumptions)

1. **The live path is the graph-vertex path, not the SQLite repo path.** The Opportunities &
   Recommendations page calls `POST /recommendations/generate/{advisor_id}` →
   `app.recommendations.service.RecommendationService.generate_for_advisor(persist=True)`, which
   upserts `phx_dm_recommendation` vertices (status `"PRESENTED"`) into the in-memory
   `FoundationGraphStore`. The SQLite table `phx_dm_local_recommendation`
   (`app/recommendations/recommendation_repository.py`) is only written by the older
   `app/services/recommendation_service.py` path, which the live UI does not exercise.
2. **The live feedback path never updates recommendation status.** `/feedback-learning/submit` →
   `app.feedback.service.FeedbackLearningService.submit()` writes feedback/outcome/learning-signal
   vertices and moves the bandit weight — but touches no status anywhere. (The status-mapping code
   in `app/services/feedback_learning_service.py` belongs to the dormant parallel path.) This is
   the root cause of 12.8 and the thing 13.1 fixes for real.
3. **Recommendation and opportunity IDs are deterministic**: `OPP_MANAGEDMIX_A001_v2.0` →
   `REC_OPP_MANAGEDMIX_A001_v2.0`. Regeneration produces the same IDs. This is what makes a
   durable lifecycle keyed by recommendation_id possible at all.
4. **`generate_for_advisor(persist=True)` clobbers status on every call** — it re-upserts the
   vertex with `"status": "PRESENTED"`. It is called by the page load, by
   `InsightDataCollector.collect_for_scope`, and by `ChatContextAssembler._assemble_raw`
   (line ~192). Therefore status CANNOT authoritatively live on the graph vertex; it must live in
   SQLite and be merged back into every generation/read.
5. **The in-memory graph store resets on restart** (`get_foundation_store()` reloads the 185 CSVs;
   `MockGraphClient.runtime_vertices/runtime_edges` are process-memory only). Any injected impact
   transaction must be replayed from SQLite at boot.
6. **Mock upserts are immediately query-visible**: `MockGraphClient._upsert` writes directly into
   `store.vertices` / `store.out_index` / `store.in_index`, so an injected
   `phx_dm_revenue_transaction` + `phx_dm_transaction_for_advisor` edge is instantly picked up by
   `advisor_transactions()` — i.e., by Revenue Analytics, GQ-005 trend, and everything
   transaction-based, with zero service changes. Edge names not in the manifest are accepted
   (indexes are defaultdicts), so a new runtime edge type works in mock mode without schema load.
7. **Two different revenue sources power the three target screens**:
   - Transaction-based (live store): `RevenueAnalyticsService.analytics()`, Advisor 360's
     `revenue_trend` (GQ-005), `ScopeRollupService._comparison()`.
   - Snapshot-based (SQLite `feature_snapshots`, survives restart): Advisor 360's
     `feature_snapshot.features.revenue_ltm/aum_total` KPIs, `ScopeRollupService._aggregate()`
     (Executive Dashboard totals). `revenue_ltm` is computed in
     `FeatureEngineeringService.compute_advisor_snapshot()` from GQ-004 over transactions — so a
     recompute after transaction injection moves it by exactly the injected amount.
8. **Dates**: seeded transactions span 2023-08-01 → 2026-07-28; all pipeline services use
   `as_of = date(2026, 7, 3)`. An impact transaction dated `2026-07-03` falls inside the existing
   reference month (2026-07), so `RevenueAnalyticsService._current_months` gains **no new month
   bucket** — MTD/QTD/YTD/LTM/ALL windows all include it and none of them shift. This is why the
   before/after can differ by *exactly* the impact amount.
9. **`app/api/main.py` has no lifespan/startup hook yet** — one must be added for boot replay.
10. **SQLite home**: `SQLiteManager` (`app/feature_store/sqlite_manager.py`) →
    `settings.sqlite_db_path` (`data/sqlite/iperform.db`). All new tables go there.

---

## 1. State machine (13.1)

### 1.1 States and transitions

Canonical states (stored UPPERCASE in the lifecycle tables and on the graph vertex):

```
OPEN  ──accept──▶  ACCEPTED ──start───▶ IN_PROGRESS
 │ │ │                │  │                   │  │
 │ │ │                │  └──complete──┐      │  └──modify──▶ MODIFIED
 │ │ │                └──modify──▶ MODIFIED  └──complete──┐
 │ │ └──reject──▶ REJECTED (terminal)                     │
 │ └────ignore──▶ IGNORED  (terminal)        COMPLETED (terminal) ◀┘
 └──────complete─▶ COMPLETED  (records an implied ACCEPTED transition first)
MODIFIED ──reopen──▶ OPEN        MODIFIED ──accept──▶ ACCEPTED
```

Allowed-transition table (the single source of truth, a module constant in
`app/recommendations/lifecycle.py`):

| from \ action | accept | start | complete | modify | reject | ignore | reopen |
|---|---|---|---|---|---|---|---|
| OPEN        | ACCEPTED | — | COMPLETED* | MODIFIED* | REJECTED | IGNORED | — |
| ACCEPTED    | — | IN_PROGRESS | COMPLETED | MODIFIED | — | — | — |
| IN_PROGRESS | — | — | COMPLETED | MODIFIED | — | — | — |
| MODIFIED    | ACCEPTED | — | — | — | — | — | OPEN |
| COMPLETED / REJECTED / IGNORED | terminal — every action rejected with 409 |

\* `OPEN → complete` and `OPEN → modify` are allowed as one-click shortcuts because the current
UI exposes Complete/Modify directly on open cards; the service records the implied
`OPEN → ACCEPTED` transition row first, then the requested one — so the audit trail always shows
the spec-formal path (`OPEN → ACCEPTED → COMPLETED`), and the demo's single-click flow keeps
working. Decisive choice: do NOT force the UI into a two-click flow.

`MODIFIED` is deliberately non-terminal and re-enters via `reopen`→OPEN or `accept`→ACCEPTED
(spec: "ACCEPTED → MODIFIED → (re-enters OPEN or ACCEPTED)").

Terminal statuses: `COMPLETED`, `REJECTED`, `IGNORED`. Terminal ⇒ `allowed_actions = []` ⇒ UI
buttons disabled (server-driven, not client-guessed — see §8).

### 1.2 Enum extension

`app/models/recommendations.py` — extend, never remove (existing values stay verbatim):

```python
class RecommendationStatus(StrEnum):
    GENERATED = "generated"        # legacy synonym of OPEN (old SQLite rows)
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IGNORED = "ignored"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"    # NEW (13.1)
    MODIFIED = "modified"          # NEW (13.1)
```

Normalization helper in `app/recommendations/lifecycle.py`:
`canonical(status) -> str` maps `PRESENTED`/`generated`/`GENERATED`/None → `OPEN`, everything
else → `status.upper()`. All lifecycle-table writes store canonical form; reads of legacy rows
normalize on the way out.

### 1.3 Actor model

Every transition records `actor_type` ∈ `{"advisor", "manager", "system/agent"}` and a free-text
`actor_id` (e.g. `A005`, `U_MGR01`, `agent:lifecycle`). The client's "an agent can also complete
it and leave a note" case is `actor_type="system/agent"` with a `note` — no auth system involved
(persona scoping only, per the standing 5B-item-3 decision).

### 1.4 Persistence schema

All DDL executed in `RecommendationLifecycleService.initialize()` via the shared `SQLiteManager`
(same pattern as `RecommendationRepository.initialize()`), idempotent.

**(a) Extend `phx_dm_local_recommendation`** — it becomes the durable SQLite mirror of the live
pipeline's rec vertices (finally giving the table real rows from the live path). Guarded ALTERs
(check `PRAGMA table_info` first; SQLite has no `ADD COLUMN IF NOT EXISTS`):

```sql
ALTER TABLE phx_dm_local_recommendation ADD COLUMN advisor_id TEXT;
ALTER TABLE phx_dm_local_recommendation ADD COLUMN action_family TEXT;
ALTER TABLE phx_dm_local_recommendation ADD COLUMN estimated_revenue_impact REAL;
ALTER TABLE phx_dm_local_recommendation ADD COLUMN status_note TEXT;
CREATE INDEX IF NOT EXISTS idx_phx_dm_recommendation_advisor
    ON phx_dm_local_recommendation(advisor_id, status);
```

On every `generate_for_advisor(persist=True)`, each rec is ALSO upserted here (id, advisor_id,
opportunity_id, prediction_id, playbook_id, title, action_text, action_family, score=priority,
confidence, estimated_revenue_impact, status, timestamps). **Upsert rule change vs the current
`ON CONFLICT` clause: on conflict, `status` and `status_note` are NOT overwritten** (the current
clause sets `status=excluded.status`, which would clobber lifecycle state on every page load —
use a conflict clause that updates everything EXCEPT status/status_note, or read-before-write in
the lifecycle service). Only a brand-new recommendation_id gets `status='OPEN'`.

**(b) New transition-audit table:**

```sql
CREATE TABLE IF NOT EXISTS phx_dm_local_rec_status_transition (
    transition_id      TEXT PRIMARY KEY,          -- new_id("TRN")
    recommendation_id  TEXT NOT NULL,
    advisor_id         TEXT,
    from_status        TEXT NOT NULL,             -- canonical UPPERCASE
    to_status          TEXT NOT NULL,
    action             TEXT NOT NULL,             -- accept|start|complete|modify|reject|ignore|reopen
    actor_type         TEXT NOT NULL,             -- advisor | manager | system/agent
    actor_id           TEXT,
    note               TEXT,
    created_ts         TEXT NOT NULL              -- ISO-8601 UTC
);
CREATE INDEX IF NOT EXISTS idx_rec_transition_rec
    ON phx_dm_local_rec_status_transition(recommendation_id, created_ts);
CREATE INDEX IF NOT EXISTS idx_rec_transition_advisor
    ON phx_dm_local_rec_status_transition(advisor_id, created_ts);
```

**(c) Impact ledger** — see §2.

### 1.5 The lifecycle service (new module — the single choke point for status)

`app/recommendations/lifecycle.py` — `class RecommendationLifecycleService`:

```python
def effective_status(self, recommendation_id: str) -> str                      # canonical; 'OPEN' if unknown
def allowed_actions(self, status: str) -> list[str]                            # from the transition table
def apply_action(self, recommendation_id, action, actor_type, actor_id,
                 note=None) -> dict                                            # validate → transition row(s)
                                                                               # → status update (SQLite +
                                                                               # graph vertex) → side effects
def lifecycle_for(self, recommendation_id) -> dict                             # status, note, transitions[], ledger entry
def register_generated(self, rec: dict, advisor_id: str) -> dict               # SQLite mirror upsert (status-preserving);
                                                                               # returns {status, status_note, allowed_actions}
def addressed_opportunity_ids(self, advisor_id: str) -> set[str]               # for 13.5
def counts_for_advisor(self, advisor_id: str) -> dict                          # per-status counts for the summary cards
def replay_on_boot(self) -> dict                                               # §2.4; returns replay report
```

`apply_action` side effects, in order:
1. Validate against the transition table (`409 Conflict` on illegal moves — including any action
   on a terminal rec).
2. Insert transition row(s) (implied `accept` first for the OPEN-shortcut cases).
3. Update `phx_dm_local_recommendation.status` + `status_note` and upsert the graph vertex's
   `status` (via `upsert_vertex`, merging attrs — verified: mock `_upsert` merges
   `{**existing, **attrs}`, so a status-only upsert is safe and doesn't erase other attrs).
4. If `to_status == COMPLETED`: run the impact generation of §2 (ledger row, transaction
   injection, snapshot recompute, memory write) and set `status_note` to the "what changed" note.
5. Return `{recommendation_id, from_status, to_status, transition_id, status_note,
   allowed_actions, impact: {…}|None}`.

**Division of labor with the existing feedback loop (guardrail: §11.2/11.3 stays intact):**
`FeedbackLearningService.submit()` (in `app/feedback/service.py`) keeps 100% of its current
signal/weight/graph-artifact behavior, and gains ONE new call at the top:
`lifecycle.apply_action(recommendation_id, action.lower(), actor_type="advisor", actor_id=user_id,
note=reason_text)` — with its lifecycle result merged into the returned dict. The lifecycle
service NEVER touches weights/rewards; the feedback service NEVER touches status/ledger. One
choke point per concern, no double-counting. If the lifecycle rejects the action (terminal rec),
`submit()` returns the 409 up — no signal is written for an illegal transition (this also stops
weight-farming by re-clicking Complete, a real integrity fix).

---

## 2. Impact ledger (13.2)

### 2.1 Table

```sql
CREATE TABLE IF NOT EXISTS phx_dm_local_impact_ledger (
    ledger_id              TEXT PRIMARY KEY,           -- new_id("LEDG")
    recommendation_id      TEXT NOT NULL UNIQUE,       -- COMPLETED is terminal ⇒ max one entry per rec
    advisor_id             TEXT NOT NULL,
    opportunity_id         TEXT,                       -- for the 13.5 addressed-set
    action_family          TEXT,
    impact_amount          REAL NOT NULL,              -- == the rec's own estimated_revenue_impact
    impact_type            TEXT NOT NULL DEFAULT 'REVENUE',
    source_transaction_id  TEXT NOT NULL,              -- the injected phx_dm_revenue_transaction id
    note                   TEXT,                       -- the human-readable "what changed" note
    created_ts             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_impact_ledger_advisor
    ON phx_dm_local_impact_ledger(advisor_id, created_ts);
```

`impact_amount` is read from the recommendation's persisted `estimated_revenue_impact` (graph
vertex first, SQLite mirror as fallback) — **never a parameter the caller can supply**. That is
the "not an arbitrary number" guarantee, enforced structurally. Advisor resolution:
`store.out_ids("phx_dm_recommendation_for_advisor", rec_id)[0]`, fallback to the SQLite mirror's
`advisor_id`.

### 2.2 Synthetic transaction injection (completion time)

On COMPLETED, inject via the existing artifact helpers (`app/graph/artifacts.py`), which route
through the active `GraphClient` — so mock mode updates the in-memory indexes and live TigerGraph
mode upserts real vertices/edges with the same code:

```python
tx_id = f"TXIMP_{recommendation_id}"          # deterministic; UNIQUE ledger row makes it idempotent
upsert_vertex(graph, "phx_dm_revenue_transaction", "transaction_id", {
    "transaction_id": tx_id,
    "transaction_date": "2026-07-03",         # the pipeline as_of — see fact 0.8 for why
    "revenue_amount": impact_amount,
    "transaction_type": "RECOMMENDATION_IMPACT",
    "quantity": 0, "gross_amount": impact_amount,
    "source_system": "IPERFORM_LIFECYCLE",
})
upsert_edge(graph, "phx_dm_transaction_for_advisor", "phx_dm_revenue_transaction",
            "phx_dm_advisor", tx_id, advisor_id)
upsert_edge(graph, "phx_dm_transaction_from_recommendation", "phx_dm_revenue_transaction",
            "phx_dm_recommendation", tx_id, recommendation_id)   # NEW edge type — the real link back
```

Decisive choices, justified:
- **`transaction_date = as_of (2026-07-03)`**, NOT `date.today()`: the seed data's reference
  month is 2026-07 (max tx 2026-07-28). Using as_of keeps the transaction inside every existing
  period window and creates no new month bucket, so period-filtered before/after comparisons
  differ by exactly the impact. If the pipeline as_of ever moves, the rule is "clamp to the
  store's max existing transaction month."
- **`transaction_type = "RECOMMENDATION_IMPACT"`**: it shows up as its own channel in Revenue
  Analytics' `by_channel` — honest, visible attribution ("this revenue came from a completed
  recommendation"), and it makes the exact-delta verification trivial (the channel's total ==
  the ledger sum for the scope). `transaction_type` is a free string in the schema, so no
  vertex-schema change is needed for it.
- **New edge `phx_dm_transaction_from_recommendation`**: works immediately in mock mode (fact
  0.6). For live-TigerGraph parity, add the directed+reverse edge definition to
  `tigergraph/schema/` in the same commit (structural-validation pass per Section 9.3's rigor) —
  a 2-line GSQL delta, flagged in PROGRESS.md as the one schema addition Section 13 makes.
- Product/business-line edges are deliberately NOT created for the synthetic transaction — it
  appears as "Unclassified" business line, which is honest (it is program impact, not a product
  sale). State this in the ledger page's evidence line rather than faking a product link.

### 2.3 The "what changed" note format

Written to `phx_dm_local_impact_ledger.note` AND `phx_dm_local_recommendation.status_note` AND
returned to the UI:

```
Completed {YYYY-MM-DD} by {actor_type} {actor_id}: {rec title, lowercased verb form} — 
+${impact_amount:,.0f} revenue impact recorded (transaction {tx_id}). {actor note, if any}
```

Example: `Completed 2026-07-06 by advisor A005: managed-account review sprints executed —
+$48,200 revenue impact recorded (transaction TXIMP_REC_OPP_MANAGEDMIX_A005_v2.0).`

### 2.4 Boot replay (survives restart)

New FastAPI lifespan in `app/api/main.py` (none exists today):

```python
@asynccontextmanager
async def lifespan(app):
    from app.recommendations.lifecycle import RecommendationLifecycleService
    report = RecommendationLifecycleService().replay_on_boot()
    logger.info("lifecycle replay: %s", report)
    yield
app = FastAPI(..., lifespan=lifespan)
```

`replay_on_boot()`: for every ledger row, re-inject the §2.2 vertex+edges (idempotent —
deterministic tx_id; mock `_upsert` merges vertices and skips duplicate edges, verified in
`client.py` lines 293-300); for every rec with a non-OPEN lifecycle status whose graph vertex
exists (or when it is next regenerated — `register_generated` covers that case), re-apply the
status attr. Feature snapshots need NO replay: they live in SQLite (`feature_snapshots` table)
and already include the impact from the completion-time recompute (§3). Returns
`{ledger_entries_replayed, statuses_reapplied}` for the Admin/health surface and the
verification script.

---

## 3. Cross-screen propagation (13.3)

**Chosen strategy: transaction injection (automatic for transaction-based reads) + a single
per-advisor feature-snapshot recompute at completion time. No read-time overlay.**

Justification, decisively: a read-time overlay would have to be woven into every snapshot
consumer (`ScopeRollupService._aggregate`, `_top_advisors`, advisor360's `feature_snapshot`,
peer benchmarking, predictions' feature reads, …) with a double-count hazard wherever a
transaction-based number and a snapshot-based number meet (e.g. `ScopeRollupService._comparison`
already reads transactions while `_aggregate` reads snapshots). Recomputing the ONE affected
advisor's snapshot through the existing real pipeline (`FeatureEngineeringService
.compute_advisor_snapshot(advisor_id)` + `persist_snapshot`) keeps exactly one source of truth
per metric, exercises the real feature pipeline (which is the demo's point), costs one advisor's
computation (fine on the 2-core box), and persists in SQLite across restarts for free. The
overlay idea is rejected, not deferred.

Per-screen propagation, with the exact touchpoints:

| Screen | Data path | Change required | Why before/after == exactly +impact |
|---|---|---|---|
| **Revenue Analytics** | `RevenueAnalyticsService.analytics()` reads `advisor_transactions()` live from the store | **None** (injection is enough) | `kpis.total_revenue` and `monthly_trend["2026-07"]` gain exactly `impact_amount`; `by_channel` gains a `RECOMMENDATION_IMPACT` row equal to the scope's ledger sum |
| **Advisor 360 — trend** | GQ-005 `get_revenue_trend_by_scope` over transactions | **None** | July 2026 bar rises by exactly `impact_amount` |
| **Advisor 360 — KPIs** | `SnapshotStore().latest_for_entity("ADVISOR", id)` → `features.revenue_ltm` | Completion-time recompute: `snap = FeatureEngineeringService().compute_advisor_snapshot(advisor_id)`; `persist_snapshot(snap)` | `revenue_ltm` comes from GQ-004 over transactions (engineering.py line 86) → +exactly `impact_amount`. Implementer must confirm `latest_for_entity` picks the new snapshot: it orders by `snapshot_time DESC, snapshot_id DESC` — if `snapshot_time` is as_of-static and the id ties, set the recomputed snapshot's `snapshot_time` to the completion timestamp before saving. |
| **Executive Dashboard rollup** | `ScopeRollupService._aggregate()` sums `revenue_ltm` over snapshots; `_comparison()` reads transactions | **None beyond the recompute above** | Firm/Division `totals.revenue_ltm` = Σ advisor snapshots → +exactly `impact_amount`; `_comparison` picks it up via transactions independently |

Honest caveat to state in PROGRESS.md and on the ledger page: the snapshot recompute legitimately
moves OTHER derived features too (e.g. `revenue_at_risk`, `client_value`, peer gap — anything
downstream of `revenue_ltm`). That is the point of a connected system, not a bug; the
exact-delta verification pins `revenue_ltm`, `total_revenue`, and the monthly trend, and treats
other feature movement as expected consequence.

**Anchored-figures guardrail (CLAUDE.md Phase-2/11.9 rule), handled explicitly:** no base CSV,
no seeded transaction, and no existing snapshot row is ever mutated — the impact is a NEW
transaction plus a NEW snapshot version. A001/A020's anchored figures change only by
`+Σ(that advisor's ledger entries)`, which is precisely the auditable delta 13.3 demands.
Rule for the demo trace and for PROGRESS.md: run the scripted verification on a **non-anchored
advisor (use A005)**; if anyone completes a rec for A001/A020 during client hands-on use, the
ledger IS the prominent record of exactly what changed and why. Note this in PROGRESS.md when
implementing.

---

## 4. API surface (13.1/13.2/13.7)

### 4.1 Changed: `POST /recommendations/generate/{advisor_id}` and `GET /recommendations/advisor/{advisor_id}`

Each recommendation in both responses gains lifecycle fields, merged by calling
`lifecycle.register_generated(rec, advisor_id)` inside `generate_for_advisor` (persist=True path)
and `effective_status`-merge inside `list_for_advisor`:

```json
{
  "recommendation_id": "REC_OPP_MANAGEDMIX_A005_v2.0",
  "...": "existing fields unchanged",
  "status": "COMPLETED",                       // canonical, no longer always PRESENTED
  "status_note": "Completed 2026-07-06 by advisor A005: ... +$48,200 ...",
  "allowed_actions": [],                       // [] ⇒ terminal ⇒ UI disables buttons
  "terminal": true,
  "impact": {"ledger_id": "...", "impact_amount": 48200.0, "source_transaction_id": "TXIMP_..."}
}
```

The generate response also gains `"addressed_opportunities": [{opportunity_id, addressed_by,
completed_ts, note}]` (§6) and `"lifecycle_counts": {open, accepted, in_progress, completed,
rejected, ignored, modified}` from `counts_for_advisor` (replaces the workspace's derived
summary-card math with real counts).

### 4.2 New: `POST /recommendations/{recommendation_id}/transition`

```json
// request
{"action": "start", "actor_type": "system/agent", "actor_id": "agent:lifecycle",
 "note": "Auto-started after acceptance"}
// response 200
{"recommendation_id": "...", "from_status": "ACCEPTED", "to_status": "IN_PROGRESS",
 "transition_id": "TRN_...", "status_note": null, "allowed_actions": ["complete", "modify"],
 "impact": null}
// response 409 on illegal transition
{"detail": "COMPLETED is terminal; no further actions allowed for REC_..."}
```

Routing rule inside the endpoint: `start` and `reopen` call `lifecycle.apply_action` directly
(they carry no learning signal); `accept|complete|modify|reject|ignore` delegate to
`FeedbackLearningService.submit(...)` (deriving `action_family` from the rec's persisted
attributes) so the bandit weight ALWAYS moves in step with status, whichever entry point is used.
This endpoint is also the agent-completion path (13.2's "an agent can also complete it and leave
a note").

### 4.3 New: `GET /recommendations/{recommendation_id}/lifecycle`

Full audit for the explainability panel and the ledger page's expandable rows:
`{recommendation_id, status, status_note, allowed_actions, transitions: [...all rows,
chronological...], impact: {...}|null, reasoning_trace_id: "REASON_{rec_id}"}`.

### 4.4 Existing `/feedback-learning/submit` — behavior addendum, shape superset

Same request body (frontend unchanged for the 5 actions). Response gains `"lifecycle": {…}` (the
`apply_action` result). New failure mode: 409 when the rec is terminal.

### 4.5 New router: `app/api/routers/impact_ledger.py`, prefix `/impact-ledger`

- `GET /impact-ledger` → `{entries: [...], totals: {total_impact, completed_count,
  advisors_affected, by_family: {...}, by_advisor: [...]}}` — entries newest-first, each row:
  ledger fields + rec title + advisor name (resolved via the store).
- `GET /impact-ledger/advisor/{advisor_id}` → same shape filtered to one advisor.
- `GET /impact-ledger/replay-report` → last boot's `replay_on_boot()` report (Admin/health
  evidence surface).

Register both new routers in `app/api/main.py`.

---

## 5. Context-assembler integration (13.4)

Two injection points, both additive:

**(a) `ChatContextAssembler._assemble_raw` (`app/ai/chat/context_assembler.py`)** — the AI
Assistant's real grounding path. For Advisor scope (where `entity_id` is set, alongside the
existing coaching-tasks block), append one high-score context item built from SQLite (no
generation side effects):

```python
lc = RecommendationLifecycleService()
history = lc.recent_activity_for_advisor(entity_id, limit=5)   # completed/rejected/accepted recs
                                                               # + ledger entries, newest first
if history["events"]:
    lines = [f"- {e['status']} {e['created_ts'][:10]}: {e['title']} — {e['note'] or ''}"
             + (f" (recorded impact +${e['impact_amount']:,.0f}, transaction {e['source_transaction_id']})"
                if e.get("impact_amount") else "")
             for e in history["events"]]
    items.append(ChatContextItem(
        source=ChatContextSource.RECOMMENDATION_LIFECYCLE,     # NEW enum member in app/models/ai_chat.py
        title="Recommendation Actions & Recorded Impact",
        content=f"Recent recommendation lifecycle for {entity_id}:\n" + "\n".join(lines)
                + f"\nCumulative recorded impact: ${history['total_impact']:,.0f}.",
        score=95.0,
        metadata={"ledger_ids": history["ledger_ids"], "lifecycle": True},
    ))
```

Base score 95 keeps it prominent through the 11.6 reranker for questions like "what happened
with my recommendations" while still rankable-down for unrelated questions. Note the assembler's
existing recommendation block (line ~192) calls `generate_for_advisor` — after §4.1 that list
already carries the merged statuses, so the model sees `COMPLETED` there too; the new block adds
the note + measured impact, which is what the 13.4 answer must cite.

**(b) `InsightDataCollector.collect_for_scope` (`app/ai/insights/insight_data_collector.py`)** —
the AI Insight/Coaching card path. Add a `"lifecycle"` key to the returned dict for Advisor
scope: `{"completed": [...], "total_recorded_impact": float, "recent_transitions": [...]}` from
the same `recent_activity_for_advisor`, and pass it through to the insight prompt builder
(`insight_generation_engine.py`) as one grounding paragraph, same evidence treatment as
predictions/opportunities.

**(c) Memory write on terminal transitions** — in `lifecycle.apply_action`, on COMPLETED/
REJECTED, create a memory via the existing `MemoryService` (`ContextMemoryCreateRequest`,
`MemoryType.FEEDBACK`, scope=ADVISOR, facts = {recommendation_id, to_status, impact_amount,
source_transaction_id}) — mirroring the pattern already written in
`app/services/feedback_learning_service.py` lines 76-97, but on the live path. This gives the
context-memory retrieval path a second, independent route to the same fact (belt and
suspenders for 13.4's real-Claude test).

13.4's verification is an AI-behavior check ⇒ **must run with `LLM_CLIENT_MODE=claude`**, real
before/after answer text captured (standing Section-11.6 rule).

---

## 6. Regeneration rule (13.5)

The addressed-set lives in the ledger (no new table): an opportunity is **addressed** when a
COMPLETED ledger row references its `opportunity_id`.
`lifecycle.addressed_opportunity_ids(advisor_id)` = `SELECT opportunity_id FROM
phx_dm_local_impact_ledger WHERE advisor_id=? AND opportunity_id IS NOT NULL`.

In `RecommendationService.generate_for_advisor`, after `detect_for_advisor` and before the
mapping loop:

```python
addressed = self.lifecycle.addressed_opportunity_ids(advisor_id)
addressed_out = []
for opp in detection["opportunities"]:
    if opp["opportunity_id"] in addressed:
        entry = self.lifecycle.ledger_for_opportunity(opp["opportunity_id"])
        addressed_out.append({**minimal opp fields, "addressed_by": entry["recommendation_id"],
                              "completed_ts": entry["created_ts"], "note": entry["note"]})
        continue                       # no recommendation re-issued for an addressed opportunity
    ... existing mapping ...
```

Also mark the opportunity vertex itself: on completion, upsert `phx_dm_opportunity` with
`{"status": "ADDRESSED", "addressed_by_recommendation_id": rec_id}` (merge-upsert, additive
attrs) — so Graph Explorer / opportunity pages tell the same story. Two honest notes to carry
into the implementation: (1) opportunity IDs are deterministic per advisor+category+model-version,
so the exclusion is stable across regenerations — exactly what 13.5 asks; (2) the completed
action's injected revenue + snapshot recompute may ALSO genuinely change detection inputs (e.g.
a revenue-risk opportunity scoring lower afterward) — that is the deeper, real version of "the
system reflects the changed state"; the verification script records both effects. Side effect to
document: `FeedbackLearningService.impact_trend` (the ROI replay) uses
`generate_for_advisor(persist=False)`; apply the addressed-exclusion there identically (it goes
through the same method, so it is automatic) and note that replay event counts shrink as
completions accumulate — correct behavior, not drift.

---

## 7. Impact Ledger page (new surface)

- **Route**: `frontend/app/(dashboard)/impact-ledger/page.tsx` → component
  `frontend/components/impact-ledger/impact-ledger-workspace.tsx`.
- **Nav entry** (`frontend/lib/navigation.ts`, group `"AI"`, placed directly after
  "Opportunities & Recommendations" and before "Recommendation Impact / ROI"):
  `{id: "impact-ledger", label: "Impact Ledger", description: "Every completed recommendation's
  recorded consequence: the transaction it generated, linked back to its evidence chain.",
  href: "/impact-ledger", iconName: "Receipt", group: "AI", status: "new"}`.
- **Layout** (shared design system: KPI stat cards, severity tokens, delta component, currency
  util — Phase 0 components, no new primitives):
  1. Four KPI cards: Total Recorded Impact ($, green), Completed Recommendations (count),
     Advisors Affected (count), Latest Completion (date + advisor).
  2. Impact-over-time bar (Recharts, ledger entries bucketed by `created_ts` date) once ≥2
     entries exist; before that, the empty state explains how an entry is created (one line +
     link to the Recommendations page) — an honest empty state, not placeholder bars.
  3. Ledger table (scoped by the standard `AdvisorSelector`, "All advisors" default), columns:
     **Date · Advisor · Recommendation · Action Family · Impact · Transaction · Actor · Note**.
     Impact rendered with the shared currency util, green, `+$` signed. Transaction column shows
     `TXIMP_…` id with a `RECOMMENDATION_IMPACT` channel chip.
  4. Row expansion (`GET /recommendations/{id}/lifecycle`): full transition timeline
     (`OPEN → ACCEPTED → … → COMPLETED`, each with timestamp + actor + note), the ledger entry,
     and a link into Explainability for `REASON_{rec_id}` — every row traceable back through the
     13.6 evidence chain.
  5. Evidence footer (build-standard): "Source: phx_dm_local_impact_ledger (SQLite) ·
     injected phx_dm_revenue_transaction vertices via phx_dm_transaction_from_recommendation
     edges · impact amount = the recommendation's own estimated_revenue_impact."
- Data: `GET /impact-ledger` / `GET /impact-ledger/advisor/{id}` only — no client-side math
  beyond formatting.

---

## 8. Frontend changes to the Recommendations workspace (13.1/12.8 closure)

`frontend/components/recommendations/recommendations-workspace.tsx`:
1. Replace the optimistic `STATUS_FOR_ACTION` map as the source of truth: render status badge,
   `status_note`, and button enablement from the server's `status` / `allowed_actions` /
   `terminal` fields (now present in the generate response). Optimistic update stays for
   responsiveness, but is reconciled with the `lifecycle` object in the submit response.
2. Terminal recs: all five action buttons disabled (`allowed_actions` empty) + a status chip
   (COMPLETED green / REJECTED red / IGNORED slate) + the status_note rendered as the visible
   "what changed" line on the card.
3. Add a **Start** button (shown only when `allowed_actions` includes `start`) → `POST
   /recommendations/{id}/transition {action:"start", actor_type:"advisor", actor_id}` — the
   IN_PROGRESS state gets a real UI affordance, amber chip.
4. Summary cards read `lifecycle_counts` from the generate response (real per-advisor counts)
   instead of deriving from optimistic state.
5. On a `complete` response, surface the impact inline: the returned note + a link "View in
   Impact Ledger →" (`/impact-ledger`).
6. Render the `addressed_opportunities` list as a muted "Addressed" section ("no longer
   generating this recommendation — completed {date}, impact +$X") — this is 13.5 made visible.

---

## 9. The demonstrable trace (13.8) — `scripts/verify_section13_lifecycle.py`

One script, ordered steps, printing REAL values at each step and asserting the exact deltas;
plus Playwright screenshots for the UI steps (to `docs/qa_screenshots/section13/`, per the
standing screenshot rule). Advisor: **A005** (non-anchored; A001/A020 stay untouched).

| # | Step | Endpoint / screen | Recorded evidence |
|---|---|---|---|
| 1 | Baseline capture | `GET /revenue/analytics?scope_type=ADVISOR&scope_id=A005` · `GET /advisor/360/A005` · `GET /scope/...summary FIRM F001` | `total_revenue`, `monthly_trend["2026-07"]`, `feature_snapshot.features.revenue_ltm`, firm `totals.revenue_ltm` |
| 2 | Generate recs | `POST /recommendations/generate/A005` | top rec id, `estimated_revenue_impact` **I**, `status=OPEN`, `allowed_actions` |
| 3 | Accept | `POST /feedback-learning/submit {action: ACCEPT}` | `lifecycle.to_status=ACCEPTED`, transition row id, weight delta (loop intact) |
| 4 | Start | `POST /recommendations/{id}/transition {action: start}` | `to_status=IN_PROGRESS` |
| 5 | Complete | `POST /feedback-learning/submit {action: COMPLETE}` | ledger_id, `TXIMP_…`, the "what changed" note, `allowed_actions=[]` |
| 6 | Ledger | `GET /impact-ledger/advisor/A005` | entry with `impact_amount == I` |
| 7 | Propagation | re-run step 1's three calls | each figure == baseline + **I** exactly (assert to the cent); `by_channel` contains `RECOMMENDATION_IMPACT == I` |
| 8 | Terminal UI | Playwright: /recommendations, A005 selected | screenshot: disabled buttons, COMPLETED chip, status note |
| 9 | Regenerate | `POST /recommendations/generate/A005` | completed rec's opportunity in `addressed_opportunities`, NOT re-issued; remaining recs listed |
| 10 | Restart durability | restart backend; re-run steps 6-7 | boot-replay report; same +**I** figures post-restart |
| 11 | AI awareness | `LLM_CLIENT_MODE=claude`; ask AI Assistant (A005 scope): "What has this advisor recently completed and what was the impact?" | real answer text citing the completed rec title and ~$I; the assembled context payload showing the lifecycle item |
| 12 | Cycle continues | Accept a second rec (steps 3-5 abbreviated) | second ledger entry; ledger page screenshot with 2 rows |

Steps 3/5 explicitly re-print the learning-weight before/after so the evidence shows the
Section-11.2 loop still moving — proof §13 was additive, not a rebuild.

---

## 10. Implementation checklist (ordered, commit-sized — for the Opus thread)

1. **Enum + lifecycle module + DDL.** Extend `RecommendationStatus` (IN_PROGRESS, MODIFIED);
   create `app/recommendations/lifecycle.py` with the transition table, `canonical()`, DDL
   (guarded ALTERs on `phx_dm_local_recommendation`, CREATE `phx_dm_local_rec_status_transition`
   + `phx_dm_local_impact_ledger`), `apply_action` WITHOUT impact side effects yet. Unit-check
   via a python one-liner: legal path OPEN→accept→start→complete rows written; illegal move
   raises. Commit.
2. **Wire generation to the lifecycle.** `generate_for_advisor`: `register_generated` per rec,
   merged status/`allowed_actions`/`status_note` in the response, `lifecycle_counts`; make the
   SQLite mirror upsert status-preserving (fix the `ON CONFLICT` clobber, fact 0.4). Verify:
   generate → curl shows OPEN; manually set a row ACCEPTED → regenerate → still ACCEPTED. Commit.
3. **Transition endpoint + feedback-service hook.** `POST /recommendations/{id}/transition`,
   `GET /recommendations/{id}/lifecycle`; `FeedbackLearningService.submit` calls `apply_action`
   first and merges `lifecycle` into its response; 409 on terminal. Verify accept/complete via
   curl updates status + writes transition rows + still moves the weight. Commit.
4. **Impact generation (13.2).** Ledger insert + §2.2 injection + note format + opportunity
   ADDRESSED upsert + memory write; snapshot recompute (`compute_advisor_snapshot` +
   `persist_snapshot`, with the `snapshot_time` bump check from §3). Verify with curl:
   before/after `revenue_ltm` and `total_revenue` differ by exactly I. Add the
   `phx_dm_transaction_from_recommendation` edge to `tigergraph/schema/` + structural check.
   Commit.
5. **Boot replay.** Lifespan in `app/api/main.py`, `replay_on_boot`, `/impact-ledger/replay-report`.
   Verify: restart backend, figures persist. Commit.
6. **Impact-ledger router** (`app/api/routers/impact_ledger.py`) + registration. Curl-verify
   shapes. Commit.
7. **Regeneration rule (13.5).** Addressed-set exclusion + `addressed_opportunities` in the
   response. Verify: regenerate after completion → rec absent, addressed entry present. Commit.
8. **Context assembler (13.4).** `ChatContextSource.RECOMMENDATION_LIFECYCLE`, assembler block,
   `InsightDataCollector.lifecycle` key, prompt-builder pass-through. Verify with real Claude
   (step 11 of §9). Commit.
9. **Frontend: recommendations workspace** (§8 items 1-6). Playwright screenshot evidence.
   Commit.
10. **Frontend: Impact Ledger page** (§7) + nav entry. Screenshot. Commit.
11. **Verification script + full §9 trace run**, screenshots to `docs/qa_screenshots/section13/`,
    PROGRESS.md updated with the real before/after numbers, the anchored-advisor note (§3), and
    the one schema delta. Commit.

Non-goals, stated to keep scope honest: no auth/roles (actor_type is a recorded field, not a
permission), no live-TigerGraph execution of the new edge (schema delta committed + structurally
validated; runtime verified in mock mode, same hardware-honesty pattern as Phase 2), no changes
to the bandit/GNN learning mechanics (Section 11.2/11.3 untouched — verified still firing in the
trace).
