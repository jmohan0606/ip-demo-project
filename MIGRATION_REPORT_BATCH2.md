# `.store` → `run_query` Migration — BATCH TWO Report

**Date:** 2026-07-10 · **Branch:** `store-migration-batch1` (continuing Batch One's branch so both ship together) · **Status:** COMPLETE (all 11 Batch Two files migrated reads-only, verified, committed)

## Top summary

**Mission (same as Batch One):** migrate the remaining readers off `get_graph_client().store`
(which always resolves to the tier-4 in-memory mock, even in real mode) onto
`get_graph_client().run_query(...)`, so the tiered client serves them from real TigerGraph
(tier 2) on the client machine. Mock remains a LOGGED fallback only. **This batch is READS-ONLY:
no write/mutation was altered anywhere** (see per-file confirmations and the lifecycle section).
Verified here against the mock tier (tier 4) — tier-2 serving is a client-machine follow-up by
design (no reachable TigerGraph in this Codespace; the constant `served_by_tier == 4` warnings
here are expected).

### Commits (ordered)

| # | Commit | File(s) | Notes |
|---|--------|---------|-------|
| 1 | `eedc4b1` | GQ-054..061 gsql + catalog/install/cases/validator + mocks | 8 new queries — **NEED LIVE INSTALL** |
| 2 | `c2b83fb` | `app/crm/service.py` | GQ-009/011; A001/A020/A044 identical |
| 3 | `1e383dd` | `app/graph/memory/memory_seeder.py` | GQ-028/030; seeded payload identical |
| 4 | `3cd600d` | `app/graph/neighborhood.py` | GQ-009/013; structure identical, latent vtype fix (see below) |
| 5 | `d9295f0` | `app/agp/mentorship.py` | GQ-002/013/051/053; pairing + ROI identical |
| 6 | `e6c3ca2` | `app/embeddings/similar_entities.py` | new GQ-054; identical across 3 entity types |
| 7 | `3e51378` | `app/agp/service.py` | new GQ-055; scorecard identical |
| 8 | `4b56bf3` | `app/repositories/state_repository.py` | new GQ-056; counts identical |
| 9 | `32947bf` | `app/coaching/service.py` + GQ-062 gsql/catalog/mock | GQ-016/042 + new GQ-057/062 |
| 10 | `a6e07e6` | `app/api/routers/search_notifications.py` | GQ-002 + new GQ-058 |
| 11 | `6442278` | `app/recommendations/service.py` | GQ-028/022 + new GQ-059; latent playbook fix (see below) |
| 12 | `bfe897e` | `app/recommendations/lifecycle.py` | GQ-028/029/009 + new GQ-060/061; deletes DEFERRED |
| 13 | `81690b0` | `app/coaching/service.py` | cleanup: drop now-unused `_store` handle |
| 14 | *(this commit)* | `MIGRATION_REPORT_BATCH2.md` | Final report |

### Parallelization actually used

11 subagents launched concurrently, one per Batch Two file, with the Batch One guardrails:
agents may NOT commit, may NOT edit `query_catalog.json` or mock modules, may NOT create new
queries (they report "NEW QUERY NEEDED" instead). Six files came back fully migrated by agents;
five reads needing new queries came back as specs. The main thread authored ALL nine new queries
(GSQL + catalog + mocks + validator), wired the seven remaining reads itself, independently
re-verified every file old-vs-new, and committed everything serially.

One agent-proposed query was **dropped before commit**: a dedicated advisor-neighborhood query
turned out to be unnecessary — the neighborhood agent proved existing GQ-009 + GQ-013 cover all
nine curated edges, which is strictly better (both are already live-installed on the client).

### New queries created — ALL `NEEDS LIVE INSTALL + VERIFY ON CLIENT MACHINE`

| ID | Name | Why (no existing query fit) | Reader(s) served | Flag |
|----|------|------------------------------|------------------|------|
| GQ-054 | `get_embeddings_by_type` | GQ-024 is per-entity, GQ-025 uses precomputed matches; the live cosine scan needs EVERY embedding of a type + display vertices | `app/embeddings/similar_entities.py` | **NEEDS LIVE INSTALL** |
| GQ-055 | `get_agp_kpi_scorecard` | GQ-014/015 print measurements/KPIs/milestones as DISJOINT sets — the measurement→KPI and measurement→month pairings are unrecoverable from them | `app/agp/service.py` `kpi_scorecard` | **NEEDS LIVE INSTALL** |
| GQ-056 | `get_memory_counts_by_type` | GQ-047 is per-scope (N+1 over every scope entity), GQ-036 counts whole vertex types only | `app/repositories/state_repository.py` `memory_counts_by_type` | **NEEDS LIVE INSTALL** |
| GQ-057 | `get_coaching_tasks` | No GQ-001..053 query touches `phx_dm_coaching_task` at all (vertex added by the Section-9 coaching CRUD feature) | `app/coaching/service.py` `tasks()` | **NEEDS LIVE INSTALL** |
| GQ-058 | `get_documents` | No query lists `phx_dm_document` (GQ-034 has no document root) | `app/api/routers/search_notifications.py` global search | **NEEDS LIVE INSTALL** |
| GQ-059 | `get_playbooks` | Playbooks reachable only as lineage of persisted recs (GQ-028/029) — unusable at generation time; GQ-031 needs persona+intent | `app/recommendations/service.py` `_playbook_for` | **NEEDS LIVE INSTALL** |
| GQ-060 | `get_recommendation_advisor` | GQ-029's PRINT excludes the advisor; the rec vertex has no advisor attribute | `app/recommendations/lifecycle.py` `_rec_attrs` | **NEEDS LIVE INSTALL** |
| GQ-061 | `get_recommendation_status_counts` | GQ-041 scope=ALL traverses advisor-attached recs only — verified undercount (misses the 60 household-level REC_HH_* recs) | `app/recommendations/lifecycle.py` `lifecycle_totals` | **NEEDS LIVE INSTALL** |
| GQ-062 | `get_coaching_task` | Read-before-write for task status updates; nothing reads one coaching task by id | `app/coaching/service.py` `update_task_status` | **NEEDS LIVE INSTALL** |

All nine: written to `docs/tigergraph_foundation/tigergraph/queries/`, SYNTAX V1 checked against
the three defect classes (type-first params ✓; traversal targets are vertex TYPES with edge
aliases, set variables only as sources ✓; one hop per SELECT ✓ — GQ-055's month/KPI joins are
each a single-hop ACCUM, GQ-054/056/058/059/061/062 are pure vertex-set filters/aggregations with
no traversal, GQ-057/060 are single hops, reverse edges used exactly as the live-verified GQ-034/
GQ-053 do). Added to `query_catalog.json` with status `created-batch2-NEEDS-LIVE-INSTALL`, to
`install_all_queries.gsql` and `tests/query_cases.json`; `validate_package.py` expected count
updated 53→62 and the new status accepted — **STATUS PASS** after every change. Every mock is
registered via `@mock_query` and returns the real nested vset shape
(`{"v_id", "v_type", "attributes": {...}}` via the `vset`/aliased-attribute helpers) — GQ-056/061
print MapAccum objects exactly as the real RESTPP response would; readers consume via
`row.get("attributes", {})` (with the defensive `row.get("attributes", row)` normalization where
an OLD mock is consumed).

**Consolidated reminder: Batch One's GQ-051, GQ-052, GQ-053 ALSO still need live install on the
client machine** — `install_all_queries.gsql` now carries all twelve (051..062).

---

## Per-file sections

### 1. `app/crm/service.py` — commit `c2b83fb`

- **Reads found (old L155–162, the only cluster):** `in_ids(phx_dm_activity_for_advisor)` +
  `vertex(phx_dm_crm_activity)` → **GQ-009** (`crm_activities` set); per-activity
  `out_ids(phx_dm_activity_for_household)` + household name → **GQ-011** per household from
  GQ-009's `households` (no single query returns the activity→household edge; composition used).
- **Output keys unchanged:** `activities, advisor_id, by_type, recent_meetings, this_week,
  upcoming` + row keys (incl. `with`, `notes_summary`, `sentiment`). Old-vs-new deep equality
  **IDENTICAL** for A001 (agent) and A001/A020/A044 (independent main-thread re-check).
- **Fallback:** original traversal only in the `results is None` branch via
  `graph_fallback_store`; per-household GQ-011 failure degrades to `"—"` for that household only.
- **Writes:** none exist in this file. `py_compile` clean; `import app.api.main` OK.

### 2. `app/graph/memory/memory_seeder.py` — commit `1e383dd`

- **Read found (old L41–48):** learning-signal lineage (`all_vertices(phx_dm_learning_signal)` →
  `out_ids(learning_updates_recommendation)` → `out_ids(recommendation_for_advisor)`) →
  **GQ-028** (advisor's rec ids) + **GQ-030 `get_feedback_learning_history`** per rec
  (`learning_links` vset). Defensive `json.loads` only when `signal_json` is a string.
- **Output unchanged:** identical signal rows (`LS_A001 CRM_EXECUTION ACCEPT 2026-07-01`);
  `seed_for_advisor` returns identical payload (5 types) old vs new (re-verified for A020 too).
- **Fallback:** original traversal only when GQ-028 or GQ-030 returns None — proven by
  monkeypatch (full 5-type result preserved).
- **Writes untouched:** all `svc.create_memory(...)` MemoryService writes. No upserts/removes
  in-file.

### 3. `app/graph/neighborhood.py` — commit `3cd600d`

- **Reads found (old L64–84):** focal advisor vertex + the 9 curated `_SPEC` edge expansions +
  per-neighbor vertex attrs → **GQ-009** (8 of 9 edges: market, households, crm_opportunities,
  crm_leads, enrollments, predictions, opportunities, recommendations) + **GQ-013** (the ninth:
  `phx_dm_advisor_has_goal` → `goals`). GQ-034 was assessed first per §6 and rejected — it only
  covers the advisor/household/account/product spine. **No new query needed** (a drafted
  advisor-neighborhood query was discarded before commit — existing installed queries win).
- **Output:** top-level keys, node keys, node ids/types/groups, edge list, counts, and as-of
  hiding (6 hidden at 2026-04-01) all identical.
- **Latent-bug enrichment (same precedent as Batch One's client360 commit `9bb03af`):** `_SPEC`
  declares nonexistent vertex types `phx_dm_prediction` / `phx_dm_agp_goal` (real:
  `phx_dm_prediction_result` / `phx_dm_goal`), so those two nodes previously had EMPTY attributes
  and vid-fallback labels. Via the queries they now carry real attributes (labels
  `GOAL001`→`AGP Revenue Growth Goal`, `PRED_A001`→`ACTIVE`). Displayed `type` strings and as-of
  filtering derivation are unchanged by construction (still keyed off `_SPEC`).
- **Fallback:** GQ-009 None → entire original `_SPEC` store traversal; GQ-013-only failure →
  just the goal edge falls back. Forced-failure run produced the identical 19-node/18-edge
  structure. **Writes:** none in file.

### 4. `app/agp/mentorship.py` — commit `d9295f0`

- **Reads found → mapping:** advisor names (L47) → **GQ-053** (`ALL`) name map; advisor
  enumeration (L52/65/82/204) → **GQ-002** via `resolve_scope_advisor_ids_graph`; per-advisor
  enrollments (L53–54) → **GQ-013**; monthly revenue (L168 `advisor_transactions`) → **GQ-051**
  (`scope_type=ADVISOR`, all-time window). GQ-039 assessed and rejected (its
  `scoped_enrollments` carry no advisor linkage).
- **Output:** `mentor_pairing()` and `program_roi()` FULLY IDENTICAL old vs new (agent + main
  re-check). Query-dispatch spy: GQ-013 ×120, GQ-051 ×43 served; 0 fallback warnings.
- **Fallback:** `self._store = graph_fallback_store(...)` used only after `run_catalog_query`
  returns None (or inside the common helpers' logged fallbacks). **Writes:** none in file.

### 5. `app/embeddings/similar_entities.py` — new **GQ-054** — commit `e6c3ca2`

- **Reads found:** full-type `phx_dm_embedding` scan (old L41) + per-entity display attrs
  (old L64) → **GQ-054 `get_embeddings_by_type`** (embeddings + the type's display vertices in
  one call; cosine + top-k stay client-side, exactly as before).
- **Output identical** old vs new for ADVISOR (A001/A020), HOUSEHOLD (H0001/H0100), ACCOUNT,
  unknown ids, and unknown entity types; forced-fallback run identical too.
- **Fallback:** original `_embeddings_by_entity` store scan kept verbatim, reached only when
  GQ-054 is unavailable (display attrs then read per-vertex from the store as before).
- **Writes:** none in file (pure reader).

### 6. `app/agp/service.py` — new **GQ-055** — commit `3e51378`

- **Read found (old L139–171, the only residual):** `kpi_scorecard`'s five-edge traversal
  (advisor → enrollment → milestone_progress → [milestone month] → kpi_measurement → kpi) →
  **GQ-055 `get_agp_kpi_scorecard`** flat `kpi_measurement_rows` (the measurement→KPI /
  measurement→month pairing GQ-014/015 cannot provide). Rows with an empty `kpi_id` are skipped,
  mirroring the store path's `continue` for measurements without a KPI edge; `milestone_month`
  0 → None mirrors the missing-milestone label behavior.
- **Output identical** for A001/A020/A044/nonexistent; untouched `track_status` re-checked
  identical; forced-fallback identical. Everything else in the file was already on `run_query`
  (GQ-013/014/016/017/039) — untouched.
- **Fallback:** original traversal verbatim in the `rows is None` branch via
  `graph_fallback_store`. **Writes:** none in file.

### 7. `app/repositories/state_repository.py` — new **GQ-056** — commit `4b56bf3`

- **Read found (old L283, the ONLY `.store` reference):** `memory_counts_by_type` global scan of
  `phx_dm_context_memory` grouped by `memory_type` → **GQ-056 `get_memory_counts_by_type`**
  (MapAccum). Falsy types map to "Unknown" as before.
- **Already on run_query (no change needed):** memories (GQ-047), learning weights (GQ-044),
  impact ledger (GQ-045), transitions (GQ-046).
- **Output identical** (SEMANTIC 28 / EPISODIC 27 / PREFERENCE 27 / OUTCOME 27 / REASONING 27,
  same order); forced-fallback identical; missing-entry warning branch exercised (module uses
  `_log`, verified live).
- **Writes untouched (all listed, none altered):** `self._linker.upsert_memory` /
  `upsert_conversation_turn` / `upsert_reasoning_trace`; `self._upsert.upsert_vertex`
  `phx_dm_learning_weight`, `phx_dm_impact_ledger` + its two edges, `phx_dm_recommendation`,
  `phx_dm_rec_status_transition` + `transition_of_recommendation`. No deletes exist in file.

### 8. `app/coaching/service.py` — new **GQ-057/GQ-062** — commits `32947bf`, `81690b0`

- **Reads found → mapping:** sessions/reviews/advisor-name (old L61–78/46) → **GQ-016**
  (`coaching`/`reviews`/`advisor` sets); persona users (old L51) → **GQ-042** (`user` set);
  manager-assigned tasks (old L119–121) → **new GQ-057 `get_coaching_tasks`** (assigning user
  taken from the task's own `created_by_user_id` — `create_task` always writes the assigned_by
  edge to that same user, and seed data matches, verified in CSV); task read-before-write in
  `update_task_status` (old L167) → **new GQ-062 `get_coaching_task`**.
- **Output identical** for A001/A020/A044/nonexistent across `advisor()`, `tasks()`,
  `open_tasks_for_context()`; `update_task_status` same-status update and not-found behavior
  identical; forced-fallback identical; agent additionally proved the GQ-016 fallback identical
  under monkeypatch. Cleanup commit removed the now-unused `self._store` handle.
- **Writes untouched (all listed, none altered):** `upsert_vertex(phx_dm_coaching_task)` in
  `create_task` and in `update_task_status`; `upsert_edge(phx_dm_coaching_task_for_advisor)`;
  `upsert_edge(phx_dm_coaching_task_assigned_by)`. No deletes exist in file.

### 9. `app/api/routers/search_notifications.py` — new **GQ-058** — commit `a6e07e6`

- **Reads found → mapping:** global-search advisors+households (old L25–34) → **GQ-002**
  (`scope_type=ALL`); notifications advisor enumeration (old L59–63) → **GQ-002**
  (`entity_type=ADVISOR`; GQ-035 assessed and rejected — different source/semantics: this feed
  derives live from feature snapshots, which are SnapshotStore reads, not `.store`, untouched);
  knowledge-document listing (old L43) → **new GQ-058 `get_documents`** (title matching stays
  client-side).
- **Output identical** across 5 search queries (advisor/household/document/no-match branches all
  exercised) and the 16-item notification feed; document-only forced fallback identical.
- **Fallback:** store paths only in `rows is None` / `doc_items is None` branches.
  **Writes:** none exist in file.

### 10. `app/recommendations/service.py` — new **GQ-059** — commit `6442278`

- **Reads found → mapping:** `list_for_advisor` (old L234–249) → **GQ-028**; latest feature
  snapshot for save-scenario (old L269–271) → **GQ-022** (edge-vs-attribute equivalence verified
  60/60 by the agent); `_playbook_for` (old L106/109) → **new GQ-059 `get_playbooks`**
  (category match then first-playbook default, exactly the old client-side logic).
- **Output:** `list_for_advisor` IDENTICAL (A001/A020, full deep equality); snapshot id
  identical. **One intentional value enrichment (latent gap fixed, reported openly, Batch One
  precedent):** the old `_playbook_for` returned playbooks ONLY when the client was literally a
  `MockGraphClient` instance — under the session's tiered client it always returned `None`, so
  every generated recommendation carried `playbook_id: null`. Verified old-vs-new
  `generate_for_advisor(A020)`: the ONLY difference is `playbook_id: null → "PB001"` (scores,
  ranks, evidence, reasoning all identical). In real mode this also makes the
  `recommendation_uses_playbook` lineage real, which is what the old code's own comment promised
  ("via installed query once added to the catalog").
- **Fallback:** original store scan behind the query (logged); forced-fallback identical to the
  new query path. **Writes untouched (all listed, none altered):** `upsert_vertex`
  (`phx_dm_simulation_scenario`, `phx_dm_recommendation` ×2); `upsert_edge`
  (`scenario_for_advisor`, `recommendation_for_advisor` ×2, `recommendation_uses_feature_snapshot`
  ×2, `recommendation_addresses_opportunity`, `recommendation_based_on_prediction`,
  `recommendation_uses_playbook`); `write_reasoning_trace` ×2. No deletes in file.

### 11. `app/recommendations/lifecycle.py` — §5 SPECIAL — new **GQ-060/GQ-061** — commit `bfe897e` (MANDATORY SECTION)

**Reads migrated (store path = logged fallback only for each):**
- `_rec_attrs` rec attributes + addressed opportunity → **GQ-029**; rec→advisor hop → **new
  GQ-060 `get_recommendation_advisor`** (SQLite mirror enrichment preserved unchanged after it).
- `counts_for_advisor` → **GQ-028** (statuses from the `recommendations` vset).
- `recent_activity_for_advisor` rec-title map → **GQ-028** (one call).
- `_advisor_name` → **GQ-009**; `_rec_title` → **GQ-029**.
- `lifecycle_totals` → **new GQ-061 `get_recommendation_status_counts`** (GQ-041 scope=ALL was
  tried by the agent and REVERTED: it returned 12/status vs the correct 24/status because 60
  household-level REC_HH_* recs are not advisor-attached — the new query aggregates the full
  vertex set).
- Verified: `_rec_attrs` (REC_A001/REC_A020/REC_HH_H0030), `counts_for_advisor`,
  `recent_activity_for_advisor`, `lifecycle_for`, `lifecycle_totals` (open/accepted/in_progress/
  completed/rejected = 24 each) ALL identical old vs new; forced-failure fallbacks identical.

**Adapter upserts left untouched (exact, none altered):** `upsert_vertex`/`upsert_edge` in
`_generate_impact` (current lines 248/254/256/274 pre-final-commit numbering — impact transaction
vertex, its edges, opportunity update), in `reset_advisor` (opportunity un-address, rec status
reset), and in `replay_on_boot`. All `self.state.*` StateRepository calls and all SQLite mirror
reads/writes untouched.

**Deferred `.store.remove_vertex(...)` deletes — left EXACTLY as-is (current line numbers):**
- `app/recommendations/lifecycle.py:546` — `graph.store.remove_vertex("phx_dm_revenue_transaction", tx_id)`
- `app/recommendations/lifecycle.py:550` — `graph.store.remove_vertex("phx_dm_impact_ledger", e["ledger_id"])`
- `app/recommendations/lifecycle.py:561` — `graph.store.remove_vertex("phx_dm_rec_status_transition", tid)`

Also deliberately untouched: the `reset_advisor` enumeration reads at lines 559–565
(`all_vertices(phx_dm_rec_status_transition)`, `in_ids/out_ids(recommendation_for_advisor)`,
`vertex(phx_dm_recommendation)`) — they enumerate the exact in-memory objects the adjacent
mock-only deletes remove and the reset-upserts then mutate; migrating them to `run_query` while
the deletes stay mock-only would split the reset flow across tiers mid-operation.

**⚠️ KNOWN LIMITATION — split-brain in the reset/admin flow (real mode):** after this batch,
lifecycle READS come from real TigerGraph and UPSERTS go to real TigerGraph, but its DELETES
(`remove_vertex`, the three lines above) still hit the tier-4 mock store only — the
`GraphClient` tier interface has no delete operation (`run_query`/`upsert`/`statistics`/`health`
only). On the client machine, `reset_advisor` will therefore NOT remove the impact transaction /
impact-ledger / status-transition vertices from the live graph (the SQLite-tier cleanup and the
status-reset upserts still work). This needs a future real-TigerGraph delete path (a design
decision explicitly out of this batch's scope). The client-machine tester must know the
reset/admin delete flow does not delete from real TigerGraph. Note `reset_advisor` refuses
anchored advisors (A001/A020) by design, limiting blast radius.

---

## Final verification (Codespace, mock tier)

- **Backend boots:** `app.api.main:app` imports cleanly, **146 OpenAPI paths** — matches the
  documented route count.
- **Every migrated file:** `python -m py_compile` clean; old-vs-new output comparison against the
  pre-migration `git show HEAD:<file>` module (results per section above — every comparison
  independently re-run by the main thread, not just asserted by agents); forced-failure fallback
  equivalence proven for every newly-wired query path.
- **Foundation validator:** `validate_package.py` → **STATUS PASS** (62 queries; expected count
  and allowed statuses updated in the same commits as the queries themselves, matching the
  Batch One 50→53 practice).
- **All nine new mocks** smoke-tested through `get_graph_client().run_query(...)` returning
  `error: False` with the real nested vset/MapAccum shapes.
- **Zero unexpected fallback warnings** on the query paths during verification; the only
  warnings were the expected "served by MOCK tier (4)" notices.

## Client-machine follow-ups (cannot be verified in this Codespace)

1. **Install the 9 Batch Two queries** GQ-054..GQ-062 on the live graph — plus the standing
   reminder that Batch One's **GQ-051/052/053 also still need live install**.
   `install_all_queries.gsql` carries all twelve; per-query smoke params are in
   `tests/query_cases.json`.
2. Confirm `served_by_tier == 2` on the Batch Two screens: CRM Activities, Coaching & Reviews
   (sessions/tasks), Graph Explorer neighborhood, AGP mentor pairing/ROI and KPI scorecard,
   similar households/accounts panels, global search + notifications, Recommendations
   (list/generate/lifecycle/Business-Impact totals), Admin memory-coverage panel, Memory seeder.
3. Re-check GQ-055's MaxAccum/SumAccum accumulator prints and GQ-056/061's
   `MapAccum<STRING, SumAccum<INT>>` print shape against the live RESTPP JSON — the readers
   consume `{alias: value}` attribute maps / plain objects; if live prints wrap SumAccum values
   differently, adjust the readers' `int(...)` coercion (mock cannot prove engine-serialization
   details).
4. The GQ-059 playbook fix means recommendations generated on the client will now carry
   `playbook_id` + the `recommendation_uses_playbook` edge for the first time — spot-check one
   generated rec's lineage.
5. The lifecycle delete split-brain (section 11 above): exercise `reset_advisor` on a non-anchored
   advisor and confirm the documented behavior is acceptable until a real delete path is designed.

## What was intentionally NOT done

- No writes/mutations migrated or altered anywhere (rule 5) — every adapter
  `upsert_vertex`/`upsert_edge`/`_upsert`/`_linker` call listed per file above is byte-identical.
- Every `.store.remove_vertex(...)` delete left exactly as-is and documented (lifecycle section).
- No Batch One file modified; mock-tier internals (`app/graph/client.py`,
  `app/graph/tiered_client.py`, `app/graph/foundation_store.py`) untouched.
- No attempt to start/repair/connect to any local or remote TigerGraph.
- Branch not merged; no squash.

## Verification environment

`GRAPH_CLIENT_MODE=mock` (tier 4) in this Codespace. Per §12: mock and real tiers return
structurally identical results, so wiring + shape correctness is what is proven here; tier-2
serving, live data correctness, and query installation are the client-machine follow-ups above.
