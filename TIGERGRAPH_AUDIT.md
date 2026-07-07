# TIGERGRAPH_AUDIT — Source-of-Truth Audit (2026-07-07)

Purpose: TigerGraph is the source of truth for the client rebuild. This audit enumerates every
TigerGraph artifact location, states definitively which one the running app and the client
rebuild use, verifies it is complete and consistent (including every post-Section-9 addition),
and confirms the full current graph state is reproducible from it alone.

**Verdict up front: the single source of truth is `docs/tigergraph_foundation/`. It is complete,
consistent, and validator-PASS. The root `tigergraph/` folder is a stale legacy mirror from the
old 42-vertex build — now explicitly marked reference-only (see `tigergraph/README.md`, added by
this audit). No divergence requiring a schema fix was found.**

---

## (a) Every TigerGraph artifact location and what it contains

| Location | Contents | Role |
|---|---|---|
| **`docs/tigergraph_foundation/`** | The verified foundation package v0.2.0+, continuously extended through Sections 9–15: `tigergraph/schema/` (00_install, 01_vertices — **60 vertices**, 02_edges — **132 edges + 132 reverse**, 03_create_graph, `schema_catalog.json`), `tigergraph/loading/jobs/` (**185 loading jobs**), `tigergraph/queries/` (**50 GQ-### queries** + `query_catalog.json` + test cases), `data/manifest.json` (**192 file entries**) + `data/sample/vertices|edges/` (60 vertex CSVs / 132 edge CSVs, **156,247 rows**), validators under `scripts/` (`validate_package.py` etc.), plus the package's own backend/frontend reference code | **SOURCE OF TRUTH** |
| `tigergraph/` (repo root) | OLD 42-vertex build remnants: `schema/` (42-vertex enterprise schema; the `phx_dm_reasoning_trace` block was realigned to the canonical foundation shape in commit `a226193`, which itself labels this folder a "stale mirror, not loaded at runtime"), `queries_v1/` (20 old WebShell-friendly queries — pre-GQ-### naming), `queries_v2/` (empty placeholder README), `loading/` (one 32-line combined loading job), `sample_data/` (51 CSVs, OLD `ADV0001`-style IDs, ~2 advisors — entirely different dataset from the foundation's `A001` data), `docs/schema_object_inventory.json` | **LEGACY / reference-only** |
| `app/graph/tigergraph/` | Live adapter **code** (not schema/data): `mcp_client.py`, `mcp_library_client.py`, `rest_client.py`, `schema_inventory.py` — the Section 9.4 tier implementations | Live code, not an artifact store |
| `docs/tigergraph_mcp/` | One reference doc for the Part 12.4 MCP library integration | Docs only |
| `docs/tigergraph_corrected_screenshots/`, `docs/tigergraph_restpp_corrected_screenshots/` | QA screenshots | Evidence only |

## (b) Which location the running app + client rebuild ACTUALLY use — definitive

**`docs/tigergraph_foundation/` — on every relevant path:**

- `app/config/settings.py:125` — `foundation_dir: str = Field(default="docs/tigergraph_foundation", alias="FOUNDATION_DIR")`.
- `app/graph/foundation_store.py` — the in-memory mock graph the whole app runs on loads
  `<foundation_dir>/data/manifest.json` + `data/sample/` and the query catalog from
  `<foundation_dir>/tigergraph/queries/query_catalog.json`.
- `app/ingestion/ingestion_service.py:34` — the Data Ingestion & Sync page reads
  `docs/tigergraph_foundation/data/sample/vertices` (see ITEM 2 for the partial-registry fix).
- Foundation validators (`docs/tigergraph_foundation/scripts/validate_package.py` and siblings)
  validate this package.

**Root `tigergraph/` is referenced only by legacy/fallback code, none of it on the rebuild path:**

- `app/feature_store/csv_loader.py` (`DemoCsvLoader` → `tigergraph/sample_data`) — consumed by
  `app/feature_store/feature_engineering.py` → `app/services/feature_store_service.py`. The live
  `/features` router does **not** use this family (it uses `app/features/engineering.py` →
  `GraphClient` → foundation store). Only reachable via the agent toolbox's
  `materialize_features()` legacy method.
- `app/embeddings/graph_builder.py` (`DemoGraphBuilder` → `tigergraph/sample_data`) — behind
  `app/services/embedding_similarity_service.py`; reachable only as the **last-ditch fallback**
  in `app/scope/dashboard.py:_gnn_peers` (fires only if the ML vector client raises) and the
  legacy toolbox `build_embeddings()`. The live `/embeddings` router uses
  `app/embeddings/service.py` → foundation-backed engineering.
- `app/graph/mock/mock_graph_data_service.py` → `GraphAccessClient` → `/graph-access` router —
  frontend uses only `/graph-access/health`.

None of these legacy paths participate in the client rebuild (schema install, loading jobs,
query install, CSV load) — that flow is exclusively foundation-package driven.

## (c) Completeness + consistency of the source of truth

Every post-Section-9 addition verified present in `docs/tigergraph_foundation/tigergraph/schema/`
(grep evidence, this session):

| Addition | Vertex/Edge in schema | Query files |
|---|---|---|
| State repo: learning weights | `phx_dm_learning_weight` ✓ | `GQ-044_get_learning_weights.gsql` ✓ |
| State repo: impact ledger | `phx_dm_impact_ledger` ✓ + `impact_for_advisor` ✓ + `impact_from_recommendation` ✓ | `GQ-045_get_impact_ledger.gsql` ✓ |
| State repo: rec status transitions | `phx_dm_rec_status_transition` ✓ + `transition_of_recommendation` ✓ | `GQ-046_get_rec_status_transitions.gsql` ✓ |
| Memory by scope | `phx_dm_context_memory` (prior) | `GQ-047_get_context_memory_by_scope.gsql` ✓ |
| Graph-reasoning (Session 15) | `phx_dm_reasoning_trace` (canonical shape) ✓ + `phx_dm_reasoning_for_advisor` ✓ | `GQ-048/049/050` (advisor/scope traversal, trace retrieval) ✓ |
| Guardrail layer | `phx_dm_guardrail_event` ✓ (10 seeded rows load) | — |

**Foundation validator run this session (real output):**

```
$ cd docs/tigergraph_foundation && python scripts/validate_package.py
{ "vertices": 60, "edges": 132, "reverse_edges": 132,
  "manifest_files": 192, "data_rows": 156247, "queries": 50 }
STATUS PASS
```

Consistency note on the reasoning-trace consolidation (Part A, commit `a226193`): the divergence
found there was a **write-path** bug (memory service writing a second attribute shape + a dead
edge name), not schema duplication; the fix consolidated onto the foundation's canonical shape
and realigned the legacy mirror's copy to match. Foundation schema, manifest, and all readers
now use one representation.

## (d) Divergence handling / fixes applied

- **Two copies exist by history, not by ambiguity**: root `tigergraph/` (old build) vs
  `docs/tigergraph_foundation/` (current). The source of truth was already complete — **no
  schema/GSQL/CSV fix was needed**.
- **Fix applied by this audit:** `tigergraph/README.md` added, marking the root folder
  LEGACY / REFERENCE-ONLY with a pointer to the source of truth, so no future session (or the
  client) installs from it by mistake.
- Known naming trap, documented rather than "fixed" (renames would break existing references):
  `scripts/validate_tigergraph_foundation.py` at repo root validates the **legacy** package
  (asserts ≥40 vertices/≥8 queries against the old inventory) — the real gate is
  `docs/tigergraph_foundation/scripts/validate_package.py`.

## (e) Rebuild-from-source-of-truth-only reproduces the current state

Fresh in-process rebuild this session — `FoundationGraphStore()` loading ONLY
`docs/tigergraph_foundation/data/manifest.json` + CSVs:

```
{"vertex_types": 59, "edge_types": 129, "vertex_rows": 34070,
 "edge_rows": 122177, "row_count_mismatches": []}
A001: True
phx_dm_learning_weight 5        phx_dm_rec_status_transition 144
phx_dm_guardrail_event 10       phx_dm_reasoning_trace 120
phx_dm_transition_of_recommendation 144
```

- 34,070 + 122,177 = **156,247 rows — exactly the validator's count**, zero expected-row
  mismatches.
- 59 loaded vertex types vs 60 in schema, and 129 loaded edge types vs 132: the differences are
  **exactly the deliberately header-only, runtime-accumulated types** — `phx_dm_impact_ledger`
  (+ `impact_for_advisor`, `impact_from_recommendation`) and `phx_dm_reasoning_for_advisor`.
  Seeding impact entries would make `replay_on_boot` inject revenue on boot and silently mutate
  the anchored/verified advisor figures (Session 14 decision, still correct); reasoning-for-
  advisor edges are created live per AI answer.
- Anchored advisor `A001` present; learning weights (5 families) and the revenue-neutral
  144-row status-transition history reproduce from CSV alone (matches Session 14's
  graph-from-CSV verification: MANAGED_MIX=1.08, 144 transition vertices).

**Conclusion: a client rebuild from `docs/tigergraph_foundation/` alone — schema → loading jobs
→ CSVs per manifest → GQ-001..050 — reproduces the complete current graph, including all
intelligence-layer state, with runtime-accumulated types intentionally starting empty.**
