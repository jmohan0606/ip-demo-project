# Status Check — 2026-07-05 — 4-item Consolidation Sweep

## Status (one line each)

1. **Runtime-family backend modules deletion** — WAS not started; **now DONE** (deleted this session).
2. **`/ui-integrated` router + services removal** — WAS not started; **now DONE** (deleted this session).
3. **`/orchestration` router dedup-vs-`/agentic-ai`** — already DONE (module has no `.py` files, not registered in `main.py`).
4. **`InsightDataCollector` repoint off old `FeatureStoreService`** — already DONE (now imports the Phase-5 `app.features.engineering.FeatureEngineeringService`).

## What was completed this session (items 1 & 2)

**Item 2 — `/ui-integrated` removed (all consumers were dead code).** Deleted backend routers
`ui_integrated.py` / `ui_integrated_expanded.py`, services `ui_integrated_service.py` /
`ui_integrated_expanded_service.py`, unregistered both from `main.py`; deleted frontend clients
`integrated-ui.ts` / `integrated-expanded.ts` and the orphaned `integrated-dashboard/` component
(no route, no nav entry).

**Item 1 — dormant runtime-family cluster deleted.** Emptied the four package `__init__.py`
re-exports that were the only live tethers (`app/features`, `app/graph`, `app/knowledge`,
`app/recommendations`), then deleted:
- `app/features/`: `similarity.py`, `prediction_runtime.py`, `feature_runtime.py`
- `app/graph/`: `graph_runtime.py`, `tigergraph_production_runtime.py`
- `app/knowledge/`: `knowledge_runtime.py`, `chroma_adapter.py`, `mock_vector_store.py`
- `app/recommendations/`: `recommendation_runtime.py`, `opportunity_engine.py`,
  `learning_engine.py`, `learning_store.py`, `compliance.py` (kept the live Phase-8
  `recommendation_engine.py`, `compliance_validator.py`, `playbook_selector.py`,
  `service.py`, repository/linker)
- `app/memory/` (entire dormant dir)

Safety confirmed before deletion: no live code imported any of these (the `opportunity_engine`
importer was the *real* `app/opportunities/` package, and `native_langgraph_collaboration`'s
`graph_runtime` hit was a substring of the string `"langgraph_runtime"`, not an import).

## Verification

- Backend boots clean: `import app.api.main` OK — **36 routes** (was 38; the two `/ui-integrated`
  routers removed).
- Zero residual references to any deleted module (only remaining hit is the `"langgraph_runtime"`
  context string, not an import).
- Frontend `tsc --noEmit` exit 0; `npm run build` compiled successfully, 25/25 static pages.

## Note (out of the 4-item scope, flagged for later)

`app/services/opportunity_service.py` is dormant legacy (imports the old `FeatureStoreService`,
not wired to any router) — separate from this sweep's named items; left in place.
