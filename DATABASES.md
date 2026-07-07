# Databases & State Persistence — Architecture Alignment Audit

_Investigation only (2026-07-07). No code was changed. This documents where runtime state
actually lives today vs. where the Temporal Knowledge Graph architecture intends it to live
(TigerGraph as the "memory and intelligence backbone"), and a concrete path to close the gap._

---

## TL;DR verdict

**This is a genuine architectural divergence, not a clean local-dev fallback that swaps by config.**

- The **graph access layer IS a real swappable adapter** (`GraphClient` Protocol, selected by
  `GRAPH_CLIENT_MODE=mock|local_real|real`). Good.
- But **every durable runtime state** the architecture says belongs in TigerGraph — bandit/learning
  weights, recommendation status, impact ledger, and all 6 memory types — is written to **SQLite**
  through a **directly-constructed `SQLiteManager()` or raw `sqlite3.connect()`**, with **no
  repository/persistence adapter** in between (`app/repositories/base_repository.py` is a 5-line
  empty stub). These cannot be repointed to TigerGraph by config; each is a code refactor.
- The graph writes that DO exist for these are **secondary, best-effort mirrors** (wrapped in
  `try/except: pass`) and are **ephemeral in the default `mock` mode** (the mock graph store is
  in-memory, rebuilt from CSVs each boot). That is precisely why `replay_on_boot` rehydrates the
  impact ledger from SQLite into the graph at startup (`app/api/main.py:61`).

So: the intended vertex/edge **types mostly already exist in the schema** (a real head start), but
the **write/read paths do not flow through the graph as the authority**, and a few required types
are missing. Making TigerGraph the real backing store needs a persistence-adapter refactor + a
few schema additions (detailed at the end), not a flag flip.

---

## (a) What state lives where today

| State | Durable store (authority) | Writing module:line | Graph mirror today | Abstraction |
|---|---|---|---|---|
| **Bandit / learning weights** (move on accept/reject) | SQLite `learning_weights` | `app/recommendations/service.py:80` (`LearningWeightStore`) | none (only audit `phx_dm_learning_signal` vertex) | **Hardcoded — raw `sqlite3.connect()`** |
| **GNN outcome affinity** (11.3 FL) | SQLite `fl_family_affinity` | `app/ml/fl_finetune.py:253` | none | **Hardcoded — raw `sqlite3`** |
| **Recommendation status** (OPEN→ACCEPTED→COMPLETED) | SQLite `phx_dm_local_recommendation.status` + `phx_dm_local_rec_status_transition` | `app/recommendations/lifecycle.py:199` | best-effort `phx_dm_recommendation.status` upsert (`lifecycle.py:205`, `try/except`) | **Hardcoded — `SQLiteManager()` at `lifecycle.py:54`** |
| **Impact ledger** (13.2 completion→txn) | SQLite `phx_dm_local_impact_ledger` | `app/recommendations/lifecycle.py:248` | `phx_dm_revenue_transaction` + edges, **replayed from SQLite at boot** (`main.py:61`) | **Hardcoded — `SQLiteManager()`** |
| **6 memory types** | SQLite `phx_dm_local_context_memory` (+ `_conversation_turn`, `_reasoning_trace`) | `app/graph/memory/memory_repository.py:60/113/128` | single `phx_dm_context_memory` / `_conversation_turn` / `_reasoning_trace` vertex, ephemeral | **Hardcoded — `SQLiteManager()` at `memory_repository.py:9`** |

**Memory type population reality** (all six route through the same hardcoded `MemoryRepository`; the
graph copy is one undifferentiated `phx_dm_context_memory` vertex discriminated by a `memory_type`
attribute — not a distinct vertex per type):

| Memory type | Populated by a real runtime flow? | Notes |
|---|---|---|
| **Conversation** | ✅ Yes | `AiAssistantChatService` → `MemoryService.save_conversation_turn` |
| **Reasoning** | ⚠️ Barely | Written only via `POST /memory` endpoint / seeder — no automatic producer |
| **Semantic** | ❌ Seed-only | `memory_seeder.py:26` (`POST /memory` seed) — no organic writer |
| **Episodic** | ❌ Seed-only | `memory_seeder.py:51` |
| **Procedural** | ❌ Absent | No `PROCEDURAL` rows are ever written (seeder has a block but it is not produced organically) |
| **Preference** | ❌ Seed-only | `memory_seeder.py:96`, derived from `fl_family_affinity` |
| _(Feedback)_ | ✅ Yes | 7th type; written by `lifecycle._generate_impact` on completion (SQLite only, graph write suppressed) |

**Two parallel feedback implementations exist** (a known duplication): the REST-wired authority is
`app/feedback/service.py` (`FeedbackLearningService` → `LearningWeightStore`); a mostly-dormant
duplicate `app/services/feedback_learning_service.py` + `app/feedback/feedback_repository.py`
(`phx_dm_local_*` tables) is reachable only via `app/agents/nodes/feedback_learning_agent.py`.

## (b) Adapter-abstracted or hardcoded?

**All hardcoded.** There is no persistence adapter equivalent to `GraphClient`/`LLMClient`.
`app/repositories/base_repository.py` is an empty stub (`repository_name` string only — no
interface, no methods). `app/feature_store/sqlite_manager.py` hardcodes `import sqlite3` +
`sqlite3.connect(self.db_path)`. Every stateful service either constructs `SQLiteManager()`
directly or calls `sqlite3.connect()` directly, so **none can be repointed to TigerGraph by config
— each is a code change.**

## (c) Do the TigerGraph vertex/edge types already exist?

Mostly yes (schema: `docs/tigergraph_foundation/tigergraph/schema/`, manifest + seed CSVs under
`docs/tigergraph_foundation/data/sample/`):

| Type | In schema? | Vertex/edge target | Seed rows |
|---|---|---|---|
| Conversation memory | ✅ | `phx_dm_conversation_turn` | 10 |
| Reasoning trace | ✅ | `phx_dm_reasoning_trace` | 120 |
| Context memory (Semantic/Episodic/Preference via `memory_type`) | ✅ | `phx_dm_context_memory` | 136 |
| Procedural memory | ❌ | — (no `PROCEDURAL` rows) | 0 |
| Feedback event | ✅ | `phx_dm_feedback_event` | 180 |
| Outcome event | ✅ | `phx_dm_outcome_event` | 180 |
| Learning signal (audit) | ✅ | `phx_dm_learning_signal` | 180 |
| **Learning WEIGHT (the moving value)** | ❌ | not a vertex — only a SQLite `learning_weights` row | — |
| **Impact ledger** | ❌ | ABSENT (only referenced in query GQ-041) | — |
| **Recommendation status-transition** | ❌ | ABSENT — `status` is only a scalar attr on `phx_dm_recommendation` | — |

Linking edges all present with seed rows: `feedback_for_recommendation` (180),
`outcome_for_feedback` (180), `learning_from_outcome` (180), `learning_updates_recommendation`
(180), `conversation_creates_memory` (10), `reasoning_uses_memory` (60), plus
`memory_for_{firm,division,region,market,branch,advisor,household}`.

## (d) Verdict + recommended path to make TigerGraph the real backing store

**Verdict:** divergence, not a fallback. The types largely exist, but writes/reads don't treat the
graph as authority and there's no adapter seam to swap. Concrete path (ordered):

1. **Add a persistence adapter seam** — a `StateStore` Protocol (mirroring `GraphClient`) with
   methods per domain: learning weights, recommendation status/transitions, impact ledger, memory
   (save/query by type + scope). Select via `STATE_STORE_MODE=sqlite|tigergraph` (default `sqlite`).
2. **Refactor the ~6 hardcoded call sites** (`recommendations/service.py`, `recommendations/
   lifecycle.py`, `ml/fl_finetune.py`+`fl_service.py`, `graph/memory/memory_repository.py`) to
   depend on the interface instead of constructing `SQLiteManager()`/`sqlite3` directly. Fill in
   the empty `BaseRepository` stub or replace it.
3. **Provide two implementations**: `SqliteStateStore` (wrap today's logic verbatim — zero behavior
   change locally) and `TigerGraphStateStore` (upsert vertices/edges via `GraphClient`, and read
   back via graph traversal / installed queries).
4. **Add the 3 missing schema objects** to the foundation package: an `impact_ledger` vertex
   (+ `impact_from_recommendation`/`impact_for_advisor` edges), a `rec_status_transition` vertex
   (+ `transition_of_recommendation` edge), and — if wanted — organic Procedural-memory writes.
   Validate structurally with the package's own `scripts/validate_package.py`.
5. **Make reads traverse the graph** in TG mode (context assembler already reads memory + lifecycle;
   point those reads at the graph store when `STATE_STORE_MODE=tigergraph`).
6. **Client env**: run `GRAPH_CLIENT_MODE=real` + `STATE_STORE_MODE=tigergraph` so memory, feedback,
   status and impact live as graph vertices/edges retrieved by traversal — the intended backbone —
   while local dev keeps SQLite as the fast default. This also lets `replay_on_boot` retire in TG
   mode (durable in the graph, no SQLite→graph rehydration needed).

_Scope note: steps 1–3 are the bulk of the work (a real refactor across ~6 modules + two adapter
implementations); step 4 is a bounded schema addition with structural validation. None of it is a
config flip today._

---

## The two SQLite databases (both gitignored)

| File | Size / tables | Purpose | Source of truth for |
|---|---|---|---|
| `data/feature_store/iperform_features.db` | ~9 MB / 32 tables | **Active runtime store** — this is `settings.sqlite_db_path` (`app/config/settings.py:146`). Feature store + ingestion framework + GNN/FL/model outputs, AND the live runtime writes. | `learning_weights`, `fl_family_affinity`, `phx_dm_local_impact_ledger`, `phx_dm_local_rec_status_transition`, feature vectors, `gnn_embeddings`, ingestion checkpoints/hashes |
| `data/sqlite/iperform.db` | ~4.3 MB / 20 tables | **Preloaded demo snapshot** — built by `scripts/preload_demo_databases.py`, recorded in `data/preloaded/preloaded_demo_database_manifest.json`. `phx_dm_local_*` mirrors of graph vertices + feature vectors + insight cards. | preloaded read-side demo data (recommendations/opportunities/predictions mirrors, insight cards) |

_(Overlap note: both hold `phx_dm_local_*` tables; the feature-store DB is where live writes land,
the `iperform.db` is the seeded snapshot. Consolidating these two is a reasonable future cleanup.)_

## Gitignore + auto-recreate (nothing ships in the GitHub download)

Confirmed in `.gitignore` — all three runtime stores are ignored, so a `git clone`/download does
**not** contain them:
- `data/sqlite/*.db` — "Runtime SQLite DBs … regenerated at runtime"
- `data/feature_store/*.db` (and `**/data/feature_store/*.db`)
- `data/chroma/chroma.sqlite3` and `data/chroma/*/` — "ChromaDB runtime state … regenerated at runtime"

**Auto-recreate:**
- **SQLite schema** — every repository issues `CREATE TABLE IF NOT EXISTS` in a lazy init on first
  use (`sqlite_manager.py`, `memory_repository.py`, `feedback_repository.py`,
  `recommendation_repository.py`, `lifecycle.py`, `prediction_repository.py`, `chat_repository.py`,
  `insight_repository.py`, `ingestion/checkpoint_repository.py`, …). So an empty clone self-heals
  the schema; `scripts/init_local_storage.py` bootstraps the local stores.
- **SQLite reseed from CSVs** — `scripts/preload_demo_databases.py` (preloaded mirror),
  `scripts/generate_enterprise_demo_data.py`, `scripts/materialize_features.py`,
  `scripts/build_embeddings_similarity.py`, `scripts/train/run_all.py` (GNN/FL/model artifacts).
- **Chroma rebuild** — `scripts/ingest_sample_knowledge.py` →
  `KnowledgeManagementService().ingest_sample_knowledge()` re-ingests the corpus into the Chroma
  `PersistentClient` at `data/chroma/`; `scripts/generate_rag_corpus_docs.py` regenerates the docs.

The graph itself, in the client environment, is rebuilt from the committed
`docs/tigergraph_foundation/data/sample/*.csv` + `manifest.json` (verified in the pre-migration
data audit — see `STATUS_CHECK.md`).

---

## Reasoning-trace consolidation (single canonical representation)

There is **one** reasoning-trace representation, used by both the display path and the
reasoning-reuse path. This resolves an earlier accidental divergence where the memory-service
write path emitted a different vertex shape and a dead edge that no reader consumed.

**Canonical vertex** `phx_dm_reasoning_trace` — PK `reasoning_id`, attrs
`artifact_type, artifact_id, reasoning_steps_json, evidence_json, model_name, prompt_version,
confidence, created_at`. Authoritative def:
`docs/tigergraph_foundation/tigergraph/schema/01_vertices.gsql` + `data/manifest.json`; the
legacy top-level `tigergraph/schema/` mirror was updated to match.

**Canonical edges** (trace → target): `phx_dm_reasoning_for_prediction`,
`phx_dm_reasoning_for_opportunity`, `phx_dm_reasoning_for_recommendation`,
`phx_dm_reasoning_for_advisor` (reuse anchor), and `phx_dm_reasoning_uses_memory` /
`phx_dm_reasoning_uses_feature_snapshot` (+ `_uses_document_chunk/_uses_crm_activity/
_uses_transaction`, `_execution_generated_reasoning`) for lineage.

| Path | Writer | Reader |
|------|--------|--------|
| Pipeline artifacts (prediction/opp/rec) | `app/graph/artifacts.py::write_reasoning_trace` | `get_reasoning_trace`, client360 lineage (DISPLAY) |
| Chat/agentic reasoning-reuse | `app/ai/reasoning/graph_reasoner.py` (artifact_type `ADVISOR`/`SCOPE`) | `get_reasoning_traces_for_scope` via `phx_dm_reasoning_for_advisor` (REUSE) |
| Memory-service `/memory/reasoning-trace` | `app/services/memory_service.py` → `TigerGraphMemoryLinker.upsert_reasoning_trace` | now emits the **canonical** shape + `phx_dm_reasoning_uses_memory` + the artifact `_for_*` edge, so it appears in DISPLAY (`get_reasoning_trace`, `get_memory_timeline`) exactly like a pipeline trace |

**What changed (Part A):** `TigerGraphMemoryLinker.upsert_reasoning_trace` now writes the canonical
vertex (was: `trace_id`/`trace_type`/`conclusion`/`status`/`created_ts`); the memory-service
`conclusion` is folded in as the terminal reasoning step (matching the reuse reader's
`steps[-1]` convention) with the raw fields preserved inside `evidence_json`. The write edge was
corrected from the dead `phx_dm_reasoning_used_memory` (absent from the manifest, never read) to
the canonical `phx_dm_reasoning_uses_memory`. The SQLite mirror
(`phx_dm_local_reasoning_trace`) keeps its own columns unchanged — it is a local cache, not the
display/reuse source. Verified: explainability-by-recommendation, memory-timeline, and the
real-Claude reasoning-reuse traversal all surface the same trace. This is deliberate
consolidation, not duplication — do not re-introduce a second reasoning-trace shape.
