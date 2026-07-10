# `.store` → `run_query` Migration — BATCH ONE Report

**Date:** 2026-07-10 · **Branch:** `store-migration-batch1` · **Status:** in progress (updated continuously)

## Top summary

**Mission:** migrate the Batch One readers off `get_graph_client().store` (which always resolves
to the tier-4 in-memory mock, even in real mode) onto `get_graph_client().run_query(...)`, so the
tiered client can serve them from real TigerGraph (tier 2) on the client machine. Mock remains a
LOGGED fallback only. Verified here against the mock tier (tier 4) — tier-2 serving is a
client-machine follow-up by design (no reachable TigerGraph in this Codespace; see
TIGERGRAPH_PREFLIGHT.md — GSE ID-store corrupt, do not attempt local TG).

### Commits (ordered)

| # | Commit | File(s) | Notes |
|---|--------|---------|-------|
| 1 | `1e7aeb3` | `app/graph/queries/common.py` | Shared resolver via GQ-002 + `run_catalog_query` guard helpers |
| 2 | `9388e14` | GQ-051/052/053 gsql + catalog + mocks + validator | 3 new queries — **NEEDS LIVE INSTALL** |
| 3 | `e95badb` | `app/revenue/analytics.py` | Byte-identical output across 7 scope/period cases |
| 4 | `71d7b92` | `app/scope/rollup.py` (+ `scope_advisor_placements` helper in common.py) | Top/bottom via GQ-007, period-windowed, disjoint invariant |
| 5 | `f3d1617` | `app/scope/dashboard.py` | Markets/peers/recent-tx/names via GQ-051/053; period wired to rollup |
| 6 | `5c39f32` | `app/revenue/trend_explorer.py` | Byte-identical output across 6 dimension/granularity cases |
| — | *(pending)* | hierarchy.py, benchmarking.py, advisor360.py, client360/service.py, pipeline_trace_service.py | Step-2 parallel agents |

### Parallelization actually used

- **Step 0 (serial, alone):** `app/graph/queries/common.py` — nothing else started until the
  shared resolver was migrated, verified (7 scope cases, old-vs-new MATCH) and committed.
- **Serial chain (main thread, in order):** GQ-051/052/053 authored first (shared by the whole
  chain, avoids duplicate/conflicting query invention) → `analytics.py` → `rollup.py` →
  `dashboard.py`. `trend_explorer.py` after analytics (depends only on it).
- **Step 2 (parallel):** 5 subagents, one per file (`hierarchy.py`, `benchmarking.py`,
  `advisor360.py`, `client360/service.py`, `pipeline_trace_service.py`), launched concurrently.
  Guardrails: agents may NOT commit, may NOT edit `query_catalog.json` or mock modules, may NOT
  create new queries (they report "NEW QUERY NEEDED" back instead — prevents number collisions
  and hallucinated GSQL). Main thread reviews, re-verifies, and commits each serially.

### New queries created — ALL `NEEDS LIVE INSTALL + VERIFY ON CLIENT MACHINE`

| ID | Name | Why | Reader file(s) served | Flag |
|----|------|-----|----------------------|------|
| GQ-051 | `get_scope_transactions` | No catalog query returned raw per-transaction rows with advisor+product+household context; GQ-004/005 only return pre-aggregated sums, but the readers compute month/channel/business-line/geo/child dimensions from raw rows | analytics.py, trend_explorer.py, dashboard.py (recent transactions) | **NEEDS LIVE INSTALL** |
| GQ-052 | `get_product_category_map` | No catalog query exposes the product→subcategory→category classification chain as a lookup | analytics.py, trend_explorer.py | **NEEDS LIVE INSTALL** |
| GQ-053 | `get_scope_advisor_placements` | No catalog query returns per-advisor ancestor placement (branch/state, market, region, division, firm, ids+names); needed for geography, child-scope grouping, market ranking, peer-sibling resolution, dimension slice maps | analytics.py, rollup.py, dashboard.py, trend_explorer.py | **NEEDS LIVE INSTALL** |

All three: written to `docs/tigergraph_foundation/tigergraph/queries/`, follow SYNTAX V1 rules
(type-first params, vertex-type traversal targets with edge aliases, one hop per SELECT), reuse
the exact scope-resolution block from the already-live-verified GQ-005, added to
`query_catalog.json` with status `created-batch1-NEEDS-LIVE-INSTALL`, added to
`install_all_queries.gsql` and `tests/query_cases.json`, mock implementations registered via
`@mock_query` with the same aliased-attribute row shape the GSQL `PRINT vset[... AS alias]`
produces. `docs/tigergraph_foundation/scripts/validate_package.py` updated (query count 50→53;
the new status accepted alongside the existing one) — **STATUS PASS** after the change.

### Client-machine follow-ups (cannot be verified in this Codespace)

1. Install GQ-051, GQ-052, GQ-053 on the live graph (`install_all_queries.gsql` includes them)
   and run each once (test params in `tests/query_cases.json`).
2. Confirm `served_by_tier == 2` for the migrated pages (Executive Dashboard, Revenue Analytics,
   Revenue Trend Explorer + the Step-2 pages) — in the Codespace everything is served by tier 4
   by design, and the rule-4 "served by MOCK tier while GRAPH_CLIENT_MODE=real" warnings firing
   here is expected, not a failure.
3. Re-check the A001 top/bottom acceptance test against live data (passes against mock data —
   see below).
4. Known real-vs-mock membership nuance in existing GQ-007: the GSQL only ranks advisors that
   HAVE ≥1 transaction in the window (edge traversal); the mock scores all resolved advisors
   (zero-revenue advisors included). Shape is identical; membership can differ for advisors with
   no transactions in the window. Existing behavior, not introduced by this migration — noted
   for the reviewer.
5. Known mock-shape nuance in existing GQ-007 mock: it returns flat row dicts
   (`{advisor_id, advisor_name, revenue, transaction_count}`) where the real tier prints vset
   rows (`{v_id, attributes:{...}}`). Readers migrated in this batch normalize with
   `row.get("attributes", row)` so both shapes work. Flagged rather than "fixed" to avoid
   touching a mock that other verified code may rely on.

### Acceptance test — the A001 top/bottom bug (§7)

**Where top/bottom is actually computed:** traced to `app/scope/rollup.py`
`ScopeRollupService._top_advisors` (the Executive Dashboard consumes `rollup["top_advisors"]` /
`["bottom_advisors"]` via `app/scope/dashboard.py`).

**Root cause:** ranking was computed over per-advisor **feature snapshots** (`SnapshotStore`),
skipping advisors with no snapshot. On a machine where only some advisors have snapshots (e.g.
only A001), top-8 and bottom-8 collapse onto the same tiny set → A001 in both. (In this
Codespace all 60 advisors have snapshots, so the overlap didn't reproduce at FIRM scope here —
the fix removes the dependency entirely.)

**Fix:** ranking now comes from **GQ-007 `get_top_bottom_advisors`** — real transaction revenue
over the full resolved advisor universe on the graph, windowed by the selected Period (the Period
control is now wired through `dashboard() → rollup.summary(period=...)` → a real
start/end DATETIME window anchored to the scope's data months). Display fields are enriched from
snapshots (`revenue_ltm`, AUM, AGP status — anchored values untouched); a new `period_revenue`
field carries the actual ranking basis. A disjointness invariant is enforced: if the scope holds
fewer advisors than two full lists, the ranked universe is split in half rather than showing the
same advisors in both lists.

**Verified against mock data** (real command output in the per-file section):
FIRM/F001 (ALL and LTM), DIVISION/D01 (YTD), MARKET/M01, ADVISOR/A001 — overlap NONE in every
case; A001 never in both. Mock data was sufficient to confirm the invariant and the period
wiring (LTM vs YTD produce different period_revenue figures); confirming against live-graph
data volumes is client-machine follow-up #3.

### Deferred writes

`app/recommendations/lifecycle.py` is **not in Batch One** (§5 file list) — nothing was touched
there. Its `.store.remove_vertex(...)` writes remain as-is per rule 5 (no real-TigerGraph delete
path exists yet); they are Batch Two scope.

---

## Per-file sections

### 0. `app/graph/queries/common.py` — shared resolver (prerequisite) — commit `1e7aeb3` (+ helper in `71d7b92`)

- **`.store` usage found:** `resolve_scope_advisor_ids(store, ...)` — the shared traversal helper
  (FIRM→divisions→regions→markets→advisors, BRANCH/MARKET via in-edges) called by many services
  with `get_graph_client().store`.
- **Mapping:** new graph-facing entry point `resolve_scope_advisor_ids_graph(graph, scope_type,
  scope_id)` → existing **GQ-002 `get_scope_descendants`** (`entity_type="ADVISOR"`), parsing
  `advisor_descendants[].v_id`. The original store-based function is intentionally kept unchanged:
  (a) it IS the logged fallback, (b) the tier-4 mock implementations themselves use it —
  rewiring those would recurse (mock query → resolver → run_query → same mock query).
- **New shared helpers:** `run_catalog_query(graph, name, params)` — returns `results` or `None`;
  logs WARNING on raise/error-envelope (fallback never silent) and WARNING when
  `served_by_tier == 4` while `GRAPH_CLIENT_MODE != mock` (rule 4). `graph_fallback_store(graph)`;
  `scope_advisor_placements(graph, ...)` (GQ-053, added with the rollup commit).
- **Fallback log lines:** `"run_query(%s) raised %s: %s — falling back to local store traversal"`,
  `"run_query(%s) returned an error envelope (%s) — falling back to local store traversal"`,
  `"run_query(%s) served by MOCK tier (4) while GRAPH_CLIENT_MODE=%s — expected in the Codespace..."`.
- **Verification:** old vs new resolver for FIRM/F001, DIVISION/D01, REGION/R01, MARKET/M01,
  BRANCH/B001, ADVISOR/A001, ALL → counts 60/24/12/6/3/1/60, **MATCH** on every scope
  (sorted-set order). GQ-002 gsql checked against the three V1 defect classes: clean.
- **GQ-002 V1 check:** type-first params ✓, vertex-type targets with edge aliases ✓ (set
  variables appear only as traversal *sources*, which is valid V1), one hop per SELECT ✓.

### 1. `app/revenue/analytics.py` — commit `e95badb`

- **`.store` calls found → mapping:**
  - `resolve_scope_advisor_ids(self._store, st, scope_id)` (×2: main + per-child) → GQ-002 via
    `resolve_scope_advisor_ids_graph`.
  - `advisor_transactions(self._store, [aid])` (per advisor) + per-tx
    `out_ids("phx_dm_transaction_for_product", tx)` + `vertex("phx_dm_revenue_transaction", tx)`
    → **GQ-051 `get_scope_transactions`** (one scope-wide call; rows carry advisor_id/product_id;
    tx→product map filled from the same rows).
  - `_build_product_category_map` (`all_vertices` product/category + `out_ids`
    product_in_subcategory / subcategory_in_category) → **GQ-052 `get_product_category_map`**.
  - geography walk (`out_ids advisor_in_branch` + `vertex branch .state`) → **GQ-053
    `get_scope_advisor_placements`** (`branch_state`).
  - by_child walk (`in_ids` division_in_firm / region_in_division / market_in_region /
    advisor_in_market + `vertex` name lookups) → GQ-053 grouping (advisors grouped by their
    placement's immediate-child id/name).
- **Output keys unchanged:** `scope_type, scope_id, kpis{total_revenue, transaction_count,
  advisor_count, avg_revenue_per_advisor, months_covered, top_channel, top_business_line,
  period}, comparison{prior_revenue, change_pct, basis}, comparison_prior_period{...},
  monthly_trend, monthly_trend_prior, by_channel, by_business_line, revenue_drivers,
  by_geography, by_child, evidence{source, advisor_ids_resolved, computation}`.
- **Fallback:** every graph read has the original store path behind a `logger.warning`
  (`"...unavailable ... falling back to local store traversal"`); `_tx_category` falls back to
  the store product-edge lookup for rows not sourced from GQ-051.
- **Verification:** old module (git `HEAD` version) vs new, 7 cases — FIRM/F001 ALL+LTM,
  DIVISION/D01 YTD, REGION/R01 QTD, MARKET/M01 LTM, ADVISOR/A001 ALL+LTM — **IDENTICAL** JSON
  in all 7. Confirmed zero fallback warnings fired (run_query path served everything).
  `py_compile` clean.

### 2. `app/scope/rollup.py` — commit `71d7b92`

- **`.store` calls found → mapping:**
  - `resolve_scope_advisor_ids` (×2) → GQ-002 via `resolve_scope_advisor_ids_graph`.
  - `_child_breakdown` traversal (`in_ids` child edges + `vertex` name lookups) → GQ-053
    placements grouping.
  - `_top_advisors` advisor-name `vertex` lookups → GQ-007 row `advisor_name` /GQ-053 placements.
  - **Ranking itself** (previously SnapshotStore-ordered) → **GQ-007 `get_top_bottom_advisors`**
    (direction TOP/BOTTOM, result_limit, real DATETIME window from the selected period). GQ-007
    gsql checked against the V1 defect classes: clean.
- **Output keys:** summary keys unchanged (`scope_type, scope_id, totals, comparison,
  child_breakdown, top_advisors, bottom_advisors, evidence`); top/bottom row keys preserved
  (`advisor_id, advisor_name, revenue_ltm, aum_total, goal_attainment, agp_risk_score, status,
  reason`) **plus** new `period_revenue` (the honest ranking basis). `summary()` gained an
  optional `period` parameter (default None = ALL window; existing callers unaffected).
- **Snapshot totals (`totals`, `comparison`) are untouched** — SnapshotStore is not a graph read.
  Anchored advisor figures not modified (A001 `revenue_ltm` still comes from its snapshot).
- **Fallback:** `_top_advisors_from_snapshots` (the exact old ranking) behind
  `"get_top_bottom_advisors unavailable ... falling back to snapshot ranking"`; child breakdown
  store path behind `"child breakdown ... using local store traversal fallback"`.
- **Verification:** old vs new — `totals`/`comparison`/`child_breakdown`/`evidence` identical;
  only top/bottom differ (intended). Acceptance test output:
  `FIRM F001 (None|LTM)`, `DIVISION D01 YTD`, `MARKET M01`, `ADVISOR A001` → overlap **NONE**
  everywhere, A001 never in both; LTM vs YTD rank over different windows (top1 period_revenue
  840,009.06 vs 521,543.14). `py_compile` clean, zero fallback warnings.

### 3. `app/scope/dashboard.py` — commit `f3d1617`

- **`.store` calls found → mapping:**
  - `resolve_scope_advisor_ids` (×2: `_per_advisor_rev`, main) → GQ-002 helper.
  - `_firm_id` (`all_vertices phx_dm_firm`) → firm_id from GQ-053 placements (store fallback).
  - `_markets_under` + `_market_row` (hierarchy `in_ids` walks + name lookups) → GQ-053
    placements grouped by market.
  - `_peer_scope_ids` sibling walks (`in_ids`/`out_ids` on firm/division/region/market edges) →
    parent located from current scope's GQ-053 rows; siblings enumerated from the parent scope's
    GQ-053 rows.
  - `_advisor_benchmark` peer advisor name/market lookups → GQ-053 (ADVISOR scope) per peer.
  - `_recent_transactions` (per-advisor `in_ids transaction_for_advisor` + tx/household/product
    vertex+edge lookups) → **GQ-051** (rows already carry household_name/product_name).
  - `_name_for_scope` vertex lookups → label cache built from GQ-053 rows (store fallback).
- **Output keys unchanged** (dashboard payload and each sub-structure; recent-transaction rows
  keep `transaction_id, date, household, household_id, product, revenue_impact, type,
  advisor_name`).
- **Period wiring (§7):** `dashboard(period=...)` now passes `period` into
  `ScopeRollupService().summary(...)` so top/bottom follow the Time Period control.
- **Fallbacks:** every migrated read keeps the original store body behind a `logger.warning`
  (`"...using local store traversal fallback"` / `"recent transactions ... fallback"`).
- **Verification:** old vs new for FIRM/F001, DIVISION/D01, REGION/R01, MARKET/M01, ADVISOR/A001
  — every key identical **except** `top_advisors`/`bottom_advisors` (intended rollup change).
  FIRM LTM top/bottom overlap NONE. Zero fallback warnings. `py_compile` clean.

### 4. `app/revenue/trend_explorer.py` — commit `5c39f32`

- **`.store` calls found → mapping:**
  - `resolve_scope_advisor_ids` → GQ-002 helper.
  - `advisor_transactions` per advisor + per-tx `out_ids transaction_for_product` → **GQ-051**
    (scope-wide; tx→product map from rows).
  - `_advisor_slice_map` hierarchy walks (advisor_in_branch / advisor_in_market /
    market_in_region / region_in_division + name lookups) → **GQ-053** placements
    (`{dimension}_name` per advisor).
  - `_product_category_map` walks → **GQ-052**.
- **Output keys unchanged:** `scope_type, scope_id, dimension, granularity, start, end,
  available_months, slices, periods, evidence` (and all nested period/slice keys).
- **Fallbacks:** original store bodies behind `logger.warning` lines (`"...falling back to local
  store traversal"`, `"slice map ... fallback"`, `"get_product_category_map unavailable ..."`).
- **Verification:** old vs new across 6 cases (division/monthly FIRM, region/quarterly FIRM,
  market/monthly DIVISION, branch/monthly FIRM, advisor/monthly MARKET, business_line/quarterly
  FIRM) — **IDENTICAL** in all 6 (LLM_CLIENT_MODE=mock so driver text is deterministic). Zero
  fallback warnings. `py_compile` clean.

### 5–9. Step-2 files — *(sections appended below as each agent's work is reviewed and committed)*

---

## Verification environment

`GRAPH_CLIENT_MODE=mock` in this Codespace (tier 4). Per §12 of the task: every `run_query` here
serves from the mock tier by design; the mock and real tiers return identical result shapes, so
wiring + shape correctness is what is proven here. Tier-2 serving, live-graph counts, and new
query installation are client-machine follow-ups, flagged above.
