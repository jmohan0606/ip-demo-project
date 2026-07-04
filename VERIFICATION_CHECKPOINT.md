# Verification Checkpoint — 2026-07-03

Consolidated verification report captured before starting Phase 11. Everything below is
re-run evidence, not self-reported status. Working mode during verification:
`GRAPH_CLIENT_MODE=mock` (109,328 rows), `LLM_CLIENT_MODE=mock`, live `uvicorn app.api.main:app`.

---

## 1. TigerGraph re-verification (Phase 2) — what was actually checked

Local TigerGraph **Community Edition 4.2.3** in Docker on a 2-core / 8 GB codespace.

### Confirmed working on the real engine
| Check | Result |
|---|---|
| Schema DDL compiles | 56 vertex types + 126 edge types + graph created (`SHOW` confirms) |
| Loading jobs compile | all 182 server-side GSQL loading jobs created successfully |
| Data loads | **55 / 56 vertex types populated** — 51 via the GSQL file loader, 4 via live RESTPP |
| `RealGraphClient` live | `health()` returns healthy against `localhost:14240/restpp`; `upsert()` accepted real rows (coaching_session 72, similarity_match 212, learning_signal 36, reasoning_trace 120) |

`RealGraphClient.upsert` output (RESTPP JSON path, bypasses the CSV tokenizer):
```
health: {'healthy': True, 'mode': 'real', 'graph': 'iperform_insights_coaching_demo', 'restpp_url': 'http://localhost:14240/restpp'}
  phx_dm_coaching_session: accepted_vertices=72
  phx_dm_similarity_match: accepted_vertices=212
  phx_dm_learning_signal:  accepted_vertices=36
  phx_dm_reasoning_trace:  accepted_vertices=120
```

### 4 real-engine GSQL/loader bugs found and fixed (static analysis could not catch these)
1. **Trailing `;` after `WITH` clauses** — `gsql -f` rejects `WITH primary_id_as_attribute="true";`.
   Fixed by stripping trailing semicolons → all 56V/126E create.
2. **Uninitialized `DEFINE FILENAME`** — all 182 jobs fail semantic check as shipped; `$"col"`
   with `HEADER="true"` needs an initialized FILENAME. Fixed → all 182 compile.
3. **Missing `QUOTE="double"`** — JSON/free-text columns mis-parse on embedded commas; exactly
   the 16 JSON-bearing vertex types loaded empty. Fixed → 51/56 load via loader.
4. **`QUOTE="double"` + internal comma tokenizer bug** — isolated by controlled single-row tests:
   a field containing BOTH `""` escapes AND the separator comma is mis-tokenized, shifting the
   DATETIME column to receive JSON → "Invalid Attributes", whole row rejected. Affects the 5
   types whose JSON has internal commas (reasoning_trace, similarity_match, learning_signal,
   coaching_session, simulation_scenario). Worked around via the RESTPP JSON upsert path.

All 4 need upstreaming to the foundation package + its validators.

### NOT achievable on this hardware (documented limit, not a code defect)
- **Edge data load**: the GSQL file loader wedges/serializes badly on 2 cores (6/126 before
  stalling; restart clears it, it re-wedges). Edge job *definitions* all compile.
- **43-query `INSTALL`**: the C++ query compilation crashes/hangs the GSQL server repeatedly —
  even one query at a time, even with 2.3 GB free. This is the CLAUDE.md Section-8
  "machine can't handle it" case.

**Why this does not block the build:** query *semantics* are independently proven — the
foundation package's `validate_query_semantics` passes **43/43**, and `MockGraphClient`
implements all 43 with the same output contract, verified **43/43** against the package's own
`query_cases.json`. The only unproven item is real-engine C++ compilation of the queries, a
hardware constraint here.

**Decision (per Section 8):** `GRAPH_CLIENT_MODE=mock` remains the default working mode (fully
verified, instant, serves all 109,328 rows). `local_real` is a documented, working option on a
larger box (schema + jobs proven to install; `RealGraphClient` proven to query/upsert).

---

## 2. Full pipeline verification — real command output, advisor A001 (and A020)

All against a live server. Every stage links to the previous stage's real output IDs.

### STEP 1 — Feature engineering: `POST /features/compute/A001`
```
snapshot_id: FS_A001_20260703_v2.0    feature_count: 33
  revenue_ltm=387293.22  revenue_growth_3m_pct=23.3  managed_revenue_ratio=0.1123
  product_diversification_score=0.9745  aum_total=10018200.0  nnm_3m=102080.0
  peer_revenue_gap_pct=-41.78  pending_lead_count=2  crm_pipeline_value=405000.0
  agp_risk_score=19.1  kpi_on_track_ratio=0.275  recommendation_acceptance_rate=100.0
  advisor_degree_centrality=0.37  client_value_score=63.8  time_sensitivity_score=32   (…33 total)
lineage[managed_revenue_ratio] = {
  "source": "GQ-006 get_product_mix_by_scope",
  "evidence": {"managed_revenue": 43474.27, "total_revenue": 387293.22,
               "managed_product_ids": ["P001","P002","P049","P050"]}}
```
`0.1123 = 43474.27 / 387293.22` ✓ traceable to specific product IDs. REAL.

### STEP 2 — Predictions: `POST /predictions/run/A001`
```
PRED_REVDECL_A001_v2.0  REVENUE_DECLINE_RISK  score 16.7  INFO  confidence 0.95
  feature_snapshot_id: FS_A001_20260703_v2.0   <-- matches Step 1
  peer_revenue_gap_pct value=-41.78 -> +16.7 pts   (other features +0.0)
PRED_AGPRISK_A001_v2.0  AGP_OFF_TRACK_RISK    score 25.8  INFO  confidence 0.95
  feature_snapshot_id: FS_A001_20260703_v2.0   <-- matches Step 1
  milestone_attainment_pct=89 -> +5.0 | overdue_followup_count=3 -> +13.7 | kpi_on_track_ratio=0.275 -> +6.7
```
Both cite the exact Step-1 snapshot; every contribution `value` equals the Step-1 feature value. REAL, linked.

### STEP 3 — Opportunities: `POST /opportunities/detect/A001`
```
feature_snapshot_id: FS_A001_20260703_v2.0    opportunity_kind: AI (distinct from CRM, per CRM-003)
OPP_PIPELINE_A001_v2.0   PIPELINE_ACCELERATION  65.4  Attention  impact $129600.0
   derived_from_prediction: None   evidence: [crm_pipeline_value, weighted_pipeline_value, overdue_followup_count]
   severity components (25/25/20/15/15): {intelligence 60, business_impact 50.2, time 85, client 63.8, conf 75}
OPP_MANAGEDMIX_A001_v2.0 PRODUCT_MIX           49.5  Attention  impact $55235.76
   derived_from_prediction: None   evidence: [managed_revenue_ratio, revenue_ltm]
```
`$55,235.76 = 387293.22 × (0.35 − 0.1123) × 0.6` ✓. **Honest note:** A001 is a healthy advisor
(pred scores < 40), so the two *prediction-derived* rules correctly did NOT fire
(`derived_from_prediction: None`); the two *feature-driven* rules did. The prediction→opportunity
link is proven live on an at-risk advisor instead — see below.

### PREDICTION → OPPORTUNITY link proven on at-risk advisors (A015 / A020)
```
A015: OPP_AGPRESCUE_A015_v2.0  AGP_EXECUTION  64.6  derived_from_prediction: PRED_AGPRISK_A015_v2.0
A020: OPP_AGPRESCUE_A020_v2.0  AGP_EXECUTION  74.8  derived_from_prediction: PRED_AGPRISK_A020_v2.0
A020 prediction PRED_AGPRISK_A020: score 56.8 (>=40)  ->  OPP_AGPRESCUE_A020
     -> REC_OPP_AGPRESCUE_A020_v2.0 based_on prediction: PRED_AGPRISK_A020_v2.0
```
The link is live and fires when the prediction crosses the 40 threshold — not dead.

### STEP 4 — Recommendations: `POST /recommendations/generate/A001`
```
learning_weights at generation: {CRM_EXECUTION: 0.84, MANAGED_MIX: 1.25}
REC_OPP_MANAGEDMIX_A001_v2.0  MANAGED_MIX  priority 61.9 = base 49.5 x weight 1.25  addresses OPP_MANAGEDMIX_A001_v2.0
REC_OPP_PIPELINE_A001_v2.0    CRM_EXECUTION priority 54.9 = base 65.4 x weight 0.84  addresses OPP_PIPELINE_A001_v2.0
```
The learned weights **already re-ordered output**: MANAGED_MIX (49.5×1.25=61.9) outranks
CRM_EXECUTION (65.4×0.84=54.9) despite the lower base score. Each rec links to its Step-3 opportunity.

### STEP 5 — Evidence chain: `GET /explainability/recommendation/REC_OPP_MANAGEDMIX_A001_v2.0`
```
recommendation : [REC_OPP_MANAGEDMIX_A001_v2.0]
opportunities  : [OPP_MANAGEDMIX_A001_v2.0]
features       : [FS_A001_20260703_v2.0]
playbooks      : [PB001]
reasoning      : [REASON_REC_OPP_MANAGEDMIX_A001_v2.0]
reasoning.steps: ["Take the highest-severity open AI opportunities…","Map the opportunity category…",
                  "Apply the learned ranking weight for MANAGED_MIX (1.25)","Rank by adjusted priority…"]
reasoning.evidence: {base_priority_score: 49.5, learning_weight: 1.25, adjusted_priority_score: 61.9,
                     opportunity_id: OPP_MANAGEDMIX_A001_v2.0, playbook_id: PB001}
```
`predictions: (none)` is honest & consistent — this rec came from the feature-driven opportunity.

### STEP 6 — Feedback loop (the centerpiece): `POST /feedback-learning/submit`
```
BEFORE  weights {CRM_EXECUTION 0.84, MANAGED_MIX 1.25}   order [MANAGED_MIX 61.9, CRM_EXECUTION 54.9]
  3x COMPLETE on CRM_EXECUTION  -> weight 0.84 -> 0.94 -> 1.04 -> 1.14
  3x REJECT   on MANAGED_MIX    -> weight 1.25 -> 1.17 -> 1.09 -> 1.01
AFTER   weights {CRM_EXECUTION 1.14, MANAGED_MIX 1.01}   order [CRM_EXECUTION 74.6, MANAGED_MIX 50.0]
```
**The ranking flipped as a direct result of feedback** (MANAGED_MIX #1 → CRM_EXECUTION #1). The
loop is closed and live. Independently re-confirmed from a neutral weight reset: feedback flips
the top recommendation CRM_EXECUTION → MANAGED_MIX. Full chain (GQ-029) after an ACCEPT with
outcome shows all 8 stages non-empty: recommendation → opportunity → features → playbook →
reasoning → feedback → outcome → learning.

### AI Assistant (verified live)
```
POST /ai-chat/ask   (A001): answer grounds in real insight context ("A001 has 4 insight cards,
                    0 high-severity"), confidence 0.82, 7 reasoning steps, 3 context items
POST /agentic-ai/run(A020, recommendation-routed): recs 3, evidence 5, confidence 0.85
```

---

## 3. Flagged as incomplete / hardcoded / unverifiable

**Genuine gaps (documented, not hidden):**
- **TigerGraph edges + 43-query INSTALL not completed on this box** — hardware limit (see §1). Deferred to a larger machine; `mock` is the verified default.
- **Runtime-family backend modules remain on disk (dormant)** — `app/features` old files, `app/memory`, old `app/recommendations` runtime files, `graph_runtime`, `knowledge_runtime`. No longer reachable via any router, but still imported by `orchestration/tools.py`, the `ui_integrated` services, and the feature/embedding agent tools. Full deletion is gated on repointing those last callers.
- **`/ui-integrated/*` still live** — data source for 5 unbuilt Phase 11 pages (knowledge, whatif, integrated-dashboard, graph-explorer, documents). Scheduled for deletion during Phase 11.
- **`/orchestration` backend router retained** — real engine, no frontend; dedup-vs-`/agentic-ai` decision deferred.
- **Agentic feature/embedding agent tools** still call the old `FeatureStoreService`/`EmbeddingSimilarityService` (the 3 artifact tools — predictions/opportunities/recommendations — were rewired to the new pipeline and verified).
- **Insights generation sub-narrative** still emits an old "MockModelAdapter" note (the chat *answer* uses the new LLMClient; the insights *engine* has its own adapter — consolidation-sweep item).

**Fixed during verification:** stale `.pyc` from deleted modules removed; verification-induced
SQLite DB mutation reverted. **Hygiene flag:** runtime SQLite DBs are git-tracked
(`data/feature_store/*.db`, `data/sqlite/*.db`) — verification runs mutate them; consider gitignoring.

**Not hardcoded:** every pipeline stage above produces real, linked output — no fabricated
dictionaries survive in the pipeline path. (The remaining fake surface is `/ui-integrated`,
already flagged for deletion.)

---

## 4. Current PROGRESS.md status

**Complete & re-verified:** Section 0B audit; Phase 1 (Streamlit/scaffolding removed, GraphClient/
LLMClient adapters); Phase 3 mock (43/43 GQ queries); Phase 4 (AGP/CRM); Phases 5–9 (features →
embeddings → predictions → opportunities → recommendations → feedback, closed loop verified);
Phase 2 (real-engine validation to hardware limit); Phase 10 parts 1–5 (design system + 5 real
pipeline pages: recommendations, features-embeddings, memory-explainability, predictions,
advisor-360, ai-assistant); consolidation sweep parts 1–2.

**In progress / next:** Phase 11 breadth — command centers (Exec/DDW/RDW/MDW), Revenue
Intelligence, Hierarchy Explorer, Book of Business, AGP/CRM pages, Graph Explorer, Knowledge,
Admin, Data Health (3B); then delete `/ui-integrated` + remaining dormant runtime modules once
their consumers are rebuilt.

**Verification-pass health:** all claimed commits present on `main` (18 commits); foundation
validators 4/4 PASS; `verify_mock_queries.py` 43/43, 0 hard failures; backend boots (31 routes);
frontend `tsc` + production build green (18 routes); `.env` safe (only `.env.example` tracked,
0 leaked keys).

---

## 5. LLMClient real-Claude connectivity check — 2026-07-04

Explicitly authorized to spend real tokens. `claude-haiku-4-5-20251001`, one advisor per surface.

### Key resolution (how it's read, confirmed at runtime — not just the shell)
`app/config/settings.py` uses pydantic `BaseSettings` with `Field(alias="ANTHROPIC_API_KEY")` and
`SettingsConfigDict(env_file=".env")`. No `.env` file exists, so the value comes from the real
process environment (`os.environ`). `ClaudeLLMClient.__init__` reads `settings.anthropic_api_key`
and constructs `anthropic.Anthropic(api_key=...)`.
```
os.environ present: True | length: 108 | prefix: sk-ant-…-wAA
settings.anthropic_api_key present: True | length: 108 | prefix: sk-ant-…-wAA   <-- the APP's runtime path
settings.anthropic_model: claude-haiku-4-5-20251001
```

### Direct client probe (LLM_CLIENT_MODE=claude)
```
selected client class: ClaudeLLMClient   (asserted != MockLLMClient)
describe(): {'mode': 'claude', 'model': 'claude-haiku-4-5-20251001'}
latency: 0.97s
response: "Net new money (NNM) is the net increase in client assets from new deposits,
           withdrawals, and transfers, excluding gains or losses from investment performance."
```
Natural, correct, non-templated; ~1s real network latency (mock is ~0.000s).

### Surface-by-surface enumeration

| Surface | Wired to LLMClient? | Evidence in claude mode |
|---|---|---|
| **AI Assistant chat** `/ai-chat/ask` | ✅ **YES** | Real Claude — see below |
| AI insight summary `/insights-coaching` | ❌ **NO** — silent mock fallback | `MockModelAdapter`, 0.0000s, fixed template |
| AI coaching card | ❌ **NO** — same old path | (same old adapter) |
| Agentic-ai answer text `/agentic-ai/run` | ❌ **NO** — not LLM at all | pure Python string templating |
| `/adapters/status` | describe() only, no generation | reports active mode |

**AI Assistant chat — genuine Claude (two advisors differ substantively + real latency):**
```
[A001] latency 10.43s  -> "# Coaching Action for Advisor A001 … Review and document feedback on
                           the 4 insight cards to improve future recommendation ranking …"
[A020] latency  4.23s  -> "I appreciate your question, but I'm unable to provide a specific coaching
                           action at this time due to missing critical data. What's Missing: …"
```
A001 produces a concrete action; A020 — with thinner context — Claude *notices* and declines
differently. Deterministic mock could not produce this variation. Full HTTP path also confirmed:
```
POST /ai-chat/ask (A001)  ->  HTTP 200,  total_time 12.24s,  natural markdown answer
```

**AI insight summary / coaching card — NOT wired, silently mock:**
```
insight engine adapter class: MockModelAdapter    (LLM_CLIENT_MODE=claude is ignored here)
generate_text latency: 0.0000s
output: "Demo response generated by local MockModelAdapter. Configure OPENAI_API_KEY to enable
         OpenAI-backed responses."
```
`insight_generation_engine.py` uses `ModelAdapterFactory.create(AdapterProvider.OPENAI)`, which
without `OPENAI_API_KEY` returns `MockModelAdapter` with no error — a **silent fallback to mock**.

**Agentic-ai answer — no LLM call:** `app/agents/nodes/ai_assistant_agent.py` composes the final
answer via `'\n'.join(lines)` string templating. Its reasoning steps + evidence are real pipeline
artifacts (verified earlier), but the natural-language answer is not LLM-generated.

### Explicit findings (step 5)
1. Only the **AI Assistant chat** is wired to the Section-2 `LLMClient` and genuinely reaches Claude.
2. **Insight summary + coaching card silently fall back to mock** even in claude mode (old
   `ModelAdapterFactory` path). To route them through Claude, repoint `insight_generation_engine`
   (and the feedback/coaching narrative) to `get_llm_client()`.
3. **Agentic answer text is templated, not generated** — wire `ai_assistant_agent` to `get_llm_client()`
   if LLM-authored synthesis is wanted.
These are wiring gaps, not adapter bugs — the adapter itself works end-to-end (proven above).

### Reverted to default
`LLM_CLIENT_MODE` was only ever an inline env override for this check; the persisted default in
`settings.py` remains `mock` (confirmed `get_settings().llm_client_mode == "mock"`, no `.env`
written). Test-induced SQLite mutations reverted; tree clean. Phase 11 breadth-page work
continues on **mock** (no real tokens for routine pages).

---

## 6. Agent inventory + RAG pipeline + orchestration audit — 2026-07-04 (investigation only, no fixes)

### 6.1 Agent inventory

There are **two parallel agent systems** (the same duplicate pattern the 0B audit found elsewhere).

**System A — `app/agents/nodes/` (10 agents).** Reachable: `/agentic-ai/run` →
`AgenticAiService` → `AdvisorCoachingAgentGraph` → `AgentRegistry`. This is the one the AI
Assistant page's "agentic" mode uses. Executes via LangGraph `StateGraph` with a sequential
fallback. Every node is **pure logic/tool-calling except the final composer**:

| Node (System A) | Spec agent it maps to | Reachable? | NL output? | LLM wiring |
|---|---|---|---|---|
| `SupervisorAgent` | **Supervisor** | ✅ via /agentic-ai | no (keyword routing) | n/a |
| `ContextRetrievalAgent` | **Context** + **Memory** (one node covers both) | ✅ | no (retrieval) | n/a |
| `TigerGraphGraphAgent` | **Graph** | ✅ | no | n/a |
| `PredictionAgent` | **Prediction** | ✅ | no (calls new pipeline) | n/a |
| `OpportunityAgent` | **Opportunity** | ✅ | no (calls new pipeline) | n/a |
| `RecommendationAgent` | **Recommendation** | ✅ | no (calls new pipeline) | n/a |
| `RagKnowledgeAgent` | **Knowledge** | ✅ (but its tool is broken — see 6.2) | no (retrieval) | n/a |
| `ExplainabilityAgent` | **Explainability** | ✅ | no (consolidates evidence) | n/a |
| `FeedbackLearningAgent` | no spec match (Feedback) | ✅ | no (retrieval) | n/a |
| `AiAssistantAgent` | no spec match (final composer) | ✅ | **YES** | **hardcoded/templated `'\n'.join(lines)` — no LLM** |

**System B — `app/orchestration/agents.py` (15 agents:** Supervisor, Context, DashboardInsight,
Advisor360, Opportunity, Recommendation, Compliance, Graph, FeatureEmbedding, Knowledge,
Prediction, MemoryExplainability, FeedbackLearning, ResponseComposer). Reachable only via
`/orchestration/run` — **which has no frontend** (route deleted in the consolidation sweep) and
whose `ToolRuntime` still points at the old runtime family + fake `/ui-integrated` data. All are
pure logic/tool-callers; **none generate NL** (`ResponseComposerAgent` assembles a trace dict;
`ComplianceAgent` is a stub that stamps `"Passed"`). Effectively **dormant**.

**System C — `app/agents/ai_assistant_runtime.py` (`AiAssistantRuntime`).** Was exposed via
`/llm-activation` (deleted in the sweep) → now **orphaned/unreachable**. Notably it *does* call a
real LLM (`get_llm_runtime().chat(...)`, the old azure-first-with-mock runtime) — the only agent
code that authors NL via an LLM — but nothing reaches it anymore.

**Mapping vs the spec's 12 intended agents:**
- Implemented & reachable (System A): Supervisor, Context, Memory (folded into Context),
  Prediction, Opportunity, Recommendation, Knowledge, Graph, Explainability.
- **Revenue agent — not implemented** (no standalone class; revenue prediction is folded into
  `PredictionAgent`).
- **Coaching agent — not implemented** as a distinct agent (coaching output is produced by the
  recommendation flow + the templated composer; System B has DashboardInsight/Advisor360, not Coaching).
- **Compliance agent — implemented only in dormant System B, and only as a stub** (`rec.setdefault("compliance","Passed")`). No real compliance logic; not reachable.
- Extra (not in spec's list): `FeedbackLearningAgent`, `AiAssistantAgent` (composer).

**NL-generation summary:** across BOTH live systems, the only agent that emits natural language is
System A's `AiAssistantAgent`, and it is **templated string composition, not LLM-generated**
(consistent with the insight/coaching finding in §5). No live agent authors NL through
`get_llm_client()`. The only LLM-authoring agent (System C) is orphaned.

### 6.2 RAG pipeline — what actually exists end to end

**Ingestion (`KnowledgeManagementService.ingest_document`)** — structurally real: parse → chunk →
embed → upsert to vector store → catalog + TigerGraph document link. But:
- **Parsing is `.txt`-only.** `DocumentParser.parse` returns a literal placeholder string for
  PDF (`"[PDF placeholder extraction …] Install a PDF parser later."`) and for DOCX/PPTX. **No
  real PDF/Office extraction, no OCR anywhere.**
- **Embeddings are mock.** `KnowledgeEmbeddingService` uses `ModelAdapterFactory` →
  `MockModelAdapter.embed_text`, which is a `sha256`-seeded `random` vector — deterministic but
  **not semantic**. Vector similarity over these is effectively arbitrary. (Same silent-mock
  path as the insight bug; ignores `LLM_CLIENT_MODE`.)

**Vector store** — the architecture *intends* real ChromaDB (`chromadb.PersistentClient`), which
matches the original spec. **But at runtime it is currently broken:** `list_collections()` /
`search()` raise `chromadb.errors.InternalError: table collections already exists`. The existing
`data/chroma/chroma.sqlite3` was created by an older "sqlite persistent fallback" (when chromadb
wasn't installed — see `chroma_creation_error.txt: "No module named 'chromadb'"` and
`runtime_chroma_validation.json: implementation = sqlite_persistent_vector_collection_fallback`)
and is now schema-incompatible with the real chromadb that is presently installed. So **nothing
usable is stored in real Chroma right now**; the only populated artifact is a 4-row keyword JSON
index (`preloaded_knowledge_index.json`) used by a keyword fallback.

**Two divergent search paths (duplicate implementations):**
- **Path A — agentic RAG agent** → `AgentToolbox.search_knowledge` → `KnowledgeManagementService.search`
  → real Chroma → **fails today** with the InternalError above.
- **Path B — the Knowledge frontend** → `/ui-integrated/knowledge/search` →
  `knowledge_runtime.search` → **`MockPersistentVectorStore`** (`fallback_used: True`), returning
  canned mock documents ("Managed Account Growth Playbook", "NNM Recovery Conversation Guide").

**Is it real RAG?** No. Both paths do **retrieval only — there is no generation step over the
retrieved chunks.** `search()` returns `KnowledgeSearchResponse(query, results)`; no agent or
service feeds retrieved content into an LLM to author an answer. So "Knowledge" today =
(mock-embedded or mock-store) chunk retrieval, not retrieval-augmented *generation*.

### 6.3 Supervisor / orchestration routing

**A real routing layer exists, but only for one surface.** System A's `SupervisorAgent.run()`
performs **keyword-based intent classification** — it lowercases the question and appends agents
to a `route_plan` by keyword match (`'predict'/'risk'/'revenue'→prediction_agent`,
`'recommend'/'next best'→recommendation_agent`, `'policy'/'compliance'/'knowledge'→rag_knowledge_agent`,
etc.), always bracketed by context+graph at the front and explainability+assistant at the end.
`AdvisorCoachingAgentGraph` then executes that plan through LangGraph (sequential fallback). This
is reachable via `/agentic-ai/run` (AI Assistant "agentic" mode).

**But it is not the app's routing model.** Every other page calls its own fixed endpoint directly
(`/features`, `/predictions`, `/opportunities`, `/recommendations`, `/advisor/360`, etc.) with no
supervisor in the path. So routing today = **fixed per-page endpoints for the whole app, plus a
single real keyword-based supervisor** on the one agentic endpoint. The routing is **keyword-based,
not LLM intent-classification**. System B has its own `SupervisorAgent` too, but it's dormant
(no frontend).

### 6.4 Plainly: exists / dormant / missing / mis-wired

- **Exists & reachable:** System-A agent graph (10 nodes) via /agentic-ai with a real keyword
  supervisor; pipeline agents correctly call the new prediction/opportunity/recommendation services.
- **Dormant:** System B (`/orchestration`, no UI, old fake data); System C (`AiAssistantRuntime`,
  the only LLM-authoring agent, orphaned after /llm-activation deletion).
- **Missing entirely (architecturally absent, not just unwired):** a distinct **Revenue agent**;
  a distinct **Coaching agent**; **real Compliance logic** (only a `"Passed"` stub exists); any
  **generation step in the RAG path** (retrieval-only); real **PDF/OCR document parsing**; real
  **semantic embeddings** for knowledge (mock only).
- **Mis-wired:** the agentic composer emits templated NL instead of using `get_llm_client()`; the
  Knowledge frontend reads the mock runtime path via fake `/ui-integrated` rather than the real
  `/knowledge` service; the real `/knowledge` (Chroma) path is currently broken by a stale
  sqlite file.

---

## 7. Part 2A — mechanical fixes (2026-07-04, real before/after evidence)

### Fix 1 — Chroma repaired
- **Before:** `chromadb.PersistentClient(...).list_collections()` →
  `InternalError: table collections already exists` (stale sqlite from an old
  "sqlite_persistent_vector_collection_fallback" written when chromadb wasn't installed).
- **Action:** deleted `data/chroma/chroma.sqlite3` + `chroma_creation_error.txt`; gitignored
  chroma runtime binaries; `git rm --cached` the tracked sqlite.
- **After (clean run):**
  ```
  fresh list_collections: []
  count after add: 2
  query ids: ['t1', 't2'] | docs: ['managed account review playboo', 'NNM recovery outreach guide']
  selftest collection deleted; remaining: []
  ```
  list/add/query/delete all succeed, no errors.

### Fix 2 — real document parsing
- **Before:** `DocumentParser.parse` returned literal placeholders — PDF →
  `"[PDF placeholder extraction … Install a PDF parser later.]"`, DOCX/PPTX similar.
- **Action:** added `pypdf`, `python-docx`, `python-pptx` (deps + pyproject); implemented
  `_parse_pdf` (per-page), `_parse_docx` (paragraphs + tables), `_parse_pptx` (per-slide text).
- **After (real generated samples):**
  ```
  sample.pdf (167 chars):  "Managed Account Growth Playbook\nTarget households with over 500k…\n\nPage 2: … compliance before recommending."
  sample.docx (117 chars): "NNM Recovery Conversation Guide\nContact households with negative net cash flow…\nStage | Action"
  sample.pptx (85 chars):  "[Slide 1]\nAGP Coaching Framework\nMonth 3 milestone: revenue growth and CRM execution."
  ```
  No OCR — scanned/image-only PDFs still yield little text (documented, not a regression).

### Fix 3 — agentic composer authors via LLMClient (was templated)
- **Before:** `AiAssistantAgent` built the answer with `'\n'.join(lines)` — no LLM.
- **Action:** assembles the same structured context (top rec/opp/pred, evidence sources,
  reasoning path) and calls `get_llm_client().generate(...)`. Reasoning steps + evidence
  unchanged; only the prose is now LLM-authored. Exception-only fallback records a visible error.
- **After — mock mode:** `[mock-llm a5e853e9] … Deterministic draft based on: scope=Advisor A020 …`
  (routes through the adapter, not string-join).
- **After — claude mode (5.76s latency, real prose citing real figures):**
  ```
  **Top Recommendation for Advisor A020: Close the AGP Milestone Execution Gap**
  Your most critical action is to complete overdue lead and referral follow-ups and advance your
  highest-value CRM opportunity before the AGP milestone due date, with an estimated impact of
  $64,711.55 (priority score: 85.3). … run managed-account review sprints for your top households
  to compound momentum across multiple revenue streams. …
  ```
  Multi-second latency + figure-grounded natural language = genuine LLM authoring.

### Fix 4 — deleted dormant System B
- `git rm app/orchestration app/api/routers/orchestration.py`; stripped import+registration from
  `app/api/main.py`. No frontend refs, only its own router imported it. Backend 31→30 routes,
  `compileall` clean. `grep orchestration app/**/*.py` → empty.

### Fix 5 — deleted orphaned System C (`AiAssistantRuntime`)
- `git rm app/agents/ai_assistant_runtime.py`. Nothing imported it (post `/llm-activation`
  deletion). Its LLM-chat + memory-writeback are already covered by the new path
  (`get_llm_client()` + `AiAssistantChatService.save_conversation_turn`) — nothing unique to
  merge. `grep AiAssistantRuntime|llm-activation` → empty. Backend 30 routes.
- **Left for Part 2B:** `app/llm/llm_runtime.py` + `app/ai/adapters/*` still back the
  insight-summary/coaching-card and knowledge-embedding paths (silent-mock); rewiring those to
  `get_llm_client()` / real embeddings is 2B, not done here.

**Net after 2A:** Chroma works; real doc parsing; the one NL-authoring live agent now uses the
Section-2 adapter; two dead agent systems removed. Backend boots at 30 routes and compiles clean.

---

## 8. Part 2B — new agent logic (2026-07-04, real before/after evidence)

Scope: Revenue Agent, Coaching Agent, Compliance Agent as real distinct System-A agents wired
into the graph + Supervisor routing, plus the 2A carry-over (insight summary + coaching plan
text repointed from `ModelAdapterFactory`/`MockModelAdapter` to `get_llm_client()`).
Knowledge/embedding work deliberately NOT started (that is 2C).

### BEFORE (mock mode, real runs)

Roster: 10 agents — no revenue/coaching/compliance agent classes existed.
```
A001 "How is my revenue trending and where should I focus?"
  route: context -> graph -> prediction -> opportunity -> explainability -> assistant
  (no revenue-specific analysis anywhere; 'revenue' keyword just triggered PredictionAgent)
A020 "Coach me on what to improve this quarter"
  route: context -> graph -> explainability -> assistant     <-- NO specialist ran at all
recs carried no compliance field ("<no compliance field>"); System B's old ComplianceAgent
(deleted in 2A) had been a stub: rec.setdefault("compliance","Passed").
insight engine adapter: MockModelAdapter, generate_text latency 0.0000s, fixed template
  ("Demo response generated by local MockModelAdapter. Configure OPENAI_API_KEY …")
```

### 1. Revenue Agent — `app/agents/nodes/revenue_agent.py` (real, distinct)

Computes revenue-specific analysis over `GraphClient` (GQ-004 summary, GQ-005 monthly trend →
3-month momentum + direction, GQ-006 product mix → managed share + top products, GQ-008 market
peer benchmark → gap + percentile). Supervisor now routes
`revenue|nnm|aum|fee|production|product mix|managed|trend|peer` → `revenue_agent`.

Two advisors, same question, materially different real figures (mock mode):
```
A001: ltm=$387,293.22 momentum=+17.73% (up) managed=0.1123 peer_avg=$665,223.16 gap=-41.78% pctile=0  peers=5
      top_products [P001 $15,000.45, P007 $13,914.74, P044 $13,538.02]
A020: ltm=$539,262.90 momentum=+2.35%  (up) managed=0.1506 peer_avg=$717,599.88 gap=-24.85% pctile=33 peers=3
      top_products [P064 $19,408.92, P015 $19,086.44, P012 $18,256.08]
```
Cross-check: A001 revenue_ltm $387,293.22, managed ratio 0.1123 and peer gap −41.78% exactly
match the Phase-5 feature snapshot lineage verified in §2 (same GQ-004/GQ-006 figures) —
the agent reads the same graph, not a parallel fabrication.

### 2. Coaching Agent — `app/agents/nodes/coaching_agent.py` (LLM-authored card)

Produces the mockup AI Coaching Card (## Recommendation / ## Shoutout / ## Action Steps /
## Guideline Basis) via `get_llm_client()`, grounded in the advisor's real feature snapshot,
pipeline recommendations/opportunities/predictions, detected positive signals, playbook id and
the compliance verdict. Supervisor routes coaching intent and auto-adds
opportunity→recommendation→compliance ahead of it so the card has real artifacts to cite.
Card + grounding returned as `coaching_card` on `AgenticResponse`.

Claude mode (`claude-haiku-4-5-20251001`), full agentic run per advisor:
```
A001 (run 11.38s): grounded in FS_A001_20260703_v2.0, REC_OPP_PIPELINE_A001_v2.0, PB001,
  compliance NEEDS_REVIEW. Card cites: $405,000 CRM pipeline, 3 overdue follow-ups, $129,600
  est. impact, 23.3% revenue growth, $102,080 NNM, diversification 0.9745; Guideline Basis
  names PB001 + COMP-003 supervisory review at the $50,000 threshold.
A020 (run 8.65s):  grounded in FS_A020_20260703_v2.0, REC_OPP_AGPRESCUE_A020_v2.0, PB001,
  compliance NEEDS_REVIEW. Card cites: $1.05M pipeline, 2 overdue follow-ups, $64,711.55 est.
  impact, AGP risk 53.0, KPI on-track 37.5%, peer gap −24.85%, 9.51% growth, $262,080 NNM.
```
Different advisors → different recommendations, different shoutout figures, different action
steps — every figure traceable to that advisor's snapshot/pipeline artifacts. Multi-second real
latency; mock mode routes through the same adapter ([mock-llm …] with identical grounding).
Exception-only fallback records a visible error in `state.errors` (no silent mock swap).

### 3. Compliance Agent — `app/agents/nodes/compliance_agent.py` (real rules, not a stub)

4 real wealth-management rules evaluated against actual recommendation content/figures:
COMP-001 prohibited performance claims (BLOCK); COMP-002 managed/advisory/discretionary action
without suitability/risk-profile language (DISCLOSURE); COMP-003 estimated impact ≥ $50,000 →
supervisory principal review (REVIEW); COMP-004 confidence < 0.60 → human review (REVIEW).
Supervisor invariant: compliance_agent is ALWAYS appended when recommendation_agent runs.
Verdict annotates each rec (`compliance`, `compliance_status`) and the run
(`compliance_review` on the response).

Rule variety proven (each status reachable, not always-review):
```
"guaranteed return with no downside"          -> BLOCKED           [COMP-001]
"discretionary managed mandate" (no suitability) -> NEEDS_DISCLOSURE [COMP-002]
confidence 0.42                                -> NEEDS_REVIEW      [COMP-004]
clean small action w/ suitability note         -> PASSED            []
```
Live pipeline runs (figures are the advisors' real estimated impacts):
```
A001: 2 recs NEEDS_REVIEW (COMP-003: $129,600.00 and $55,235.76 ≥ $50,000)
A020: 3 recs NEEDS_REVIEW (COMP-003: $64,711.55 / $257,000.00 / $64,517.41)
Honest detail: the MANAGED_MIX action text already contains "document suitability …
mandate", so COMP-002 correctly does NOT fire on it — the rule reads content, not category.
```
Live HTTP (A015, compliance-intent question): route
`context -> graph -> rag_knowledge -> recommendation -> compliance -> explainability -> assistant`,
3 recs NEEDS_REVIEW [COMP-003], `recommendations[0].compliance_status == "NEEDS_REVIEW"` over
`POST /agentic-ai/run`.

### Carry-over from 2A — insight summary + coaching plan text now on LLMClient

`InsightGenerationEngine` no longer imports `ModelAdapterFactory`: executive AI summary and the
coaching-plan message are authored via `get_llm_client()` with the insight cards / focus areas
as context; LLM errors degrade visibly ("(LLM unavailable: …)"), never silently swap to mock.
```
mock  : llm client class MockLLMClient; summary/coaching text route through the adapter
claude: latency 3.90s; coaching message is natural prose grounded in the focus areas
```
**FLAGGED (pre-existing, exposed by the claude run, NOT fixed here):** the insight *data
collector* (`InsightDataCollector`) still reads the OLD `FeatureStoreService` family, whose
`advisor_growth_features` vector returns zeros for A001 (revenue 0.0, NNM 0.0, CRM 0) — Claude
honestly summarized zero-valued cards ("no measurable activity"), which proves grounding but
shows the insight cards themselves are fed by the dormant old feature family. Rewiring the
collector to the Phase-5 pipeline belongs to the consolidation sweep (already on the deferred
list: "feature/embedding agent tools still use old FeatureStoreService"), not 2B.

### Routing AFTER (same questions as BEFORE)
```
"How is my revenue trending…"  -> context -> graph -> revenue -> opportunity -> explainability -> assistant
"Coach me on what to improve…" -> context -> graph -> opportunity -> recommendation -> compliance
                                  -> coaching -> explainability -> assistant
```
Roster 10 → 13 agents (revenue_agent, compliance_agent, coaching_agent). Supervisor uses a
canonical ORDER list so compliance always follows recommendations and coaching follows
compliance (the card cites the verdict).

### Housekeeping
`AgenticResponse` gained additive fields `revenue_analysis` / `compliance_review` /
`coaching_card` (frontend unaffected). Full `compileall` clean; backend boots (30 routes);
verification-induced SQLite mutation reverted; `LLM_CLIENT_MODE=claude` was inline-env only —
persisted default remains mock. Stopped after 2B; 2C (knowledge/embeddings) not started.

---

## 9. Insight collector repointed to the Phase-5..9 pipeline (2026-07-04, pre-2C fix)

Closes the §8 flag: `InsightDataCollector` read the OLD `FeatureStoreService` family, whose
`advisor_growth_features` vector returned zeros — Claude's §8 summary honestly reported
"no measurable activity" for an advisor with $387K LTM revenue.

### Change
- `InsightDataCollector` now collects from the same pipeline everything else reads:
  `FeatureEngineeringService.compute_advisor_snapshot` (33 features + snapshot id + lineage),
  Phase-7 `predict_advisor`, Phase-8 `detect_for_advisor`, Phase-9 `generate_for_advisor`.
  Old imports (`FeatureStoreService`, old prediction/opportunity/recommendation facades) removed.
- `InsightGenerationEngine._deterministic_cards` remapped to the pipeline keys: real feature
  names (`revenue_growth_3m_pct`, `managed_revenue_ratio`, `nnm_3m`/`ncf_3m`,
  `overdue_followup_count`, `kpi_on_track_ratio`), `AGP_OFF_TRACK_RISK` on the 0-100 scale
  (was "AGP Goal Risk" on 0-1), opportunity `impact_summary`/severity mapping, recommendation
  `priority_score` (= base x learned weight, cited in the card's reasoning steps).

### BEFORE (from §8, claude mode)
```
"Advisor A001 shows no measurable activity across key performance metrics: revenue signal is
 0.0, NNM is 0.0, and NCF is 0.0, with zero CRM activity recorded…"
```

### AFTER — mock mode cards (A001), every figure from the live pipeline
```
[Medium] Revenue: LTM revenue 387293.22, 3m growth 23.3%, managed mix 11.23%, NNM 102080.0, NCF 127600.0
[Low   ] AGP: off-track risk 25.8/100; 3 overdue follow-ups; KPI on-track ratio 0.275
[Medium] Top Opportunity: PIPELINE_ACCELERATION 65.4 — "$405,000 of open CRM pipeline ($324,000 weighted)…"
[High  ] Next Best Action: priority 74.6 (base x learned CRM_EXECUTION weight 1.14 from the §2 feedback rounds)
```
All values match the §2-verified chain (FS_A001 snapshot: 387293.22 / 0.1123 / 25.8 / 65.4;
priority 74.6 is the §2 post-feedback ranking figure — the learning loop shows up in the cards).

### AFTER — claude mode (real latency, advisor-specific, non-zero)
```
A001 (5.01s): "…solid revenue momentum with LTM revenue of $387.3K and strong 3-month growth of
  23.3%, supported by 3-month NNM of $102.1K … off-track score of 25.8/100, driven primarily by
  3 overdue follow-ups and a low KPI on-track ratio of 0.275. With $405K in open CRM pipeline
  ($324K weighted) currently stalled…"
A020 (3.50s): "…LTM revenue of $539,262.90 and strong 3-month growth of 9.51% … AGP execution
  risk with an off-track score of 56.8/100 driven by 2 overdue follow-ups and a KPI on-track
  ratio of 0.375…"
```
Two advisors → different figures, all traceable (A020's 56.8 is exactly the §2-verified
PRED_AGPRISK_A020 score). Coaching-plan messages likewise cite the real focus areas. Zeros gone.

Housekeeping: full compileall clean; verification-induced SQLite mutation reverted;
`LLM_CLIENT_MODE=claude` inline-env only (persisted default remains mock). Minor cosmetic note:
Claude occasionally prefixes its summary with a markdown heading (A001 run) — presentation-layer
trim, not a grounding issue. 2C still not started.

---

## 10. Part 2C-i — real embeddings, expanded corpus, RAG generation, agent cross-wiring (2026-07-04)

Scope: backend only, per instruction. `EmbeddingClient` adapter (sentence-transformers local
default, fully replacing the sha256-random mock), 9-document corpus, semantic re-embed with
proof of discrimination, a reusable `RagGenerationService` (retrieve → grounded prompt →
`get_llm_client()` → answer + citations), wired into RagKnowledgeAgent AND the Coaching Agent.
Frontend (2C-ii) deliberately not started.

### 1. EmbeddingClient adapter (`app/llm/embedding_client.py`)

- `EmbeddingClient` Protocol (`embed` / `embed_many` / `describe`), same Section-2 pattern as
  LLMClient: SDK imports live only inside implementations.
- `LocalEmbeddingClient` — sentence-transformers `all-MiniLM-L6-v2` (384-dim, L2-normalized),
  free/local, **the new default**. `AzureOpenAIEmbeddingClient` — env-configured
  (`AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, default `text-embedding-3-small`) for the client site.
- `EMBEDDING_CLIENT_MODE=local|azure` in settings + `.env.example`; module-level singleton so
  the model loads once per process (~20s cold, instant after).
- The sha256 mock path is GONE from the live path: `KnowledgeEmbeddingService` (used by
  ingest + search) now delegates to `get_embedding_client()` — the old
  `ModelAdapterFactory`→`MockModelAdapter.embed_text` import is removed. (The
  `DeterministicEmbeddingProvider` file survives only inside the dormant runtime family, which
  is no longer reachable from any live path — see consolidation below.)
- `/adapters/status` now reports the embedding adapter (verified over HTTP):
  `"embedding_client_mode": "local", "embedding": {"mode": "local", "model":
  "sentence-transformers/all-MiniLM-L6-v2", "dimensions": 384}`.

### 2. Corpus expanded 4 → 9 documents (19 chunks)

New documents (substantive, category-spanning, in `data/documents/sample_knowledge/`):
`crm_engagement_guide.txt` (CRM Engagement), `advisor_prospecting_playbook.txt` (Playbook),
`client_review_procedures.txt` (Compliance policy incl. the $50,000 supervisory-review
threshold that COMP-003 enforces in code), `agp_program_overview.txt` (AGP Guide),
`market_research_notes_2026q2.txt` (Research) — plus the original 4 (compliance policy,
AGP coaching guide, managed-account playbook, glossary). Ingested via `ingest_sample_knowledge`
with a filename→category mapper:

```
ingested 9 documents, 19 chunks, all status=indexed  (chroma count: 19)
  DOC_… advisor_prospecting_playbook.txt  Playbook        chunks=3
  DOC_… agp_program_overview.txt          AGP Guide       chunks=3
  DOC_… client_review_procedures.txt      Compliance      chunks=3
  DOC_… crm_engagement_guide.txt          CRM Engagement  chunks=3
  DOC_… market_research_notes_2026q2.txt  Research        chunks=3   (+ the original 4)
```

Chroma collection recreated with cosine space (`hnsw:space=cosine`); old 64-dim sha256 vectors
wiped. `KnowledgeSearchResult.score` is now cosine **similarity** (1 − distance, higher =
better) instead of raw distance.

### 3. Semantic correctness — real similarity scores, right document wins every time

Five category-targeted queries, top-4 with scores (mock LLM irrelevant here — this is pure
retrieval; threshold disabled to show the full ranking):

```
"What dollar threshold requires supervisory principal review…?"
  +0.6424 client_review_procedures.txt (Compliance)      <- correct #1, next-doc gap 0.27
"How do I get more referrals from my existing clients?"
  +0.5072 advisor_prospecting_playbook.txt (Playbook)    <- correct #1
"When does an advisor's AGP milestone attainment trigger a recovery plan?"
  +0.7264 agp_program_overview.txt (AGP Guide)           <- correct #1, top-3 all AGP
"What is the standard for handling overdue follow-ups in the pipeline?"
  +0.7057 crm_engagement_guide.txt (CRM Engagement)      <- correct #1, top-3 all CRM guide
"What are clients doing with cash allocations this year?"
  +0.5911 market_research_notes_2026q2.txt (Research)    <- correct #1
```

All 5/5 rank the intended document first with clear margins — the sha256 vectors could not do
this (their similarity was arbitrary). This is semantic retrieval, not a code-path claim.

### 4. RagGenerationService (`app/knowledge/rag_service.py`) — reusable, not page-glue

`retrieve()` → top-k chunks above a 0.30 cosine floor as citable source dicts;
`answer()` → numbered source passages into a grounded prompt → `get_llm_client().generate()`
→ `{question, found, answer, sources[{chunk_id, document_id, document_name, category,
similarity, excerpt}], generated_by, retrieval}`. Same evidence bar as every pipeline stage.
Consumers wired this session: `RagKnowledgeAgent`, Coaching Agent guideline retrieval,
`AgentToolbox.ask_knowledge`, `POST /knowledge/ask`, and `/ui-integrated/knowledge/search`.

**Consolidation of the two divergent retrieval paths:** Path B
(`/ui-integrated/knowledge/search` → `knowledge_runtime` → `MockPersistentVectorStore` with
canned docs) now calls `RagGenerationService` — both live surfaces go through the ONE real
path (real embeddings + Chroma + generation). The dormant runtime-family files stay on disk
only because `memory_runtime`/`recommendation_runtime` (already on the Phase-11 deletion list)
still import them; no live route reaches them for knowledge anymore.

**Claude-mode generation, two queries, meaningfully different (real tokens, authorized):**
```
Q1 "What dollar threshold requires supervisory principal review…?"  (8.00s, claude-haiku-4-5)
  sources: client_review_procedures.txt ×3 (0.64/0.48/0.45)
  -> "…recommendations with estimated revenue impact or transfer value at or above $50,000
      require supervisory principal review before presentation to the client [1]. The
      reviewing principal must be independent of the recommending advisor's production
      credit [1]."          <- exact policy content, inline [n] citations
Q2 "How should an advisor rebuild referral-led growth in a slowing book?"  (2.75s)
  sources: advisor_prospecting_playbook.txt ×3 (0.58/0.56/0.55)
  -> four Plays summarized with per-passage citations [1][2][3], direct quotes from the
     playbook, plus the playbook's own metrics (3-5 households/quarter, 50%+ referral ratio)
```
Different questions → different documents retrieved → different grounded answers.

**Edge case — honest not-found (no hallucination, no LLM call):**
```
"How do I configure kubernetes cluster autoscaling for the trading platform?"
  found: False | sources: [] | generated_by: {mode: none, reason: no passages above threshold}
  answer: "No relevant guidance was found in the knowledge base for this question…"
```
Also verified over live HTTP: `POST /knowledge/ask` returns found=True with sources for the
policy question and found=False/0 sources for the kubernetes question (mock mode).

### 5. Agent cross-wiring

**RagKnowledgeAgent (before → after):** was retrieval-only (`search_knowledge`, evidence =
raw chunks, §6.2 finding "no generation step"). Now calls `ask_knowledge` (full RAG): stores
the generated answer + citations in `state.context['knowledge']`, evidence items carry
similarity scores and [n] numbering, reasoning step reports generation mode; honest-not-found
becomes its own reasoning step. Live agentic run (claude mode, 23.2s):
```
route: context -> graph -> rag_knowledge -> recommendation -> compliance -> explainability -> assistant
"RAG Knowledge Agent generated a grounded answer via claude LLM citing 5 document passage(s)."
RAG evidence: [1] client_review_procedures.txt 0.5721, [2] 0.4848, [3] 0.4495,
              [4] compliance_recommendation_policy.txt 0.4351, [5] agp_program_overview.txt 0.4110
```

**Coaching Agent "Guideline Basis" (before → after, same advisor A001):**
- BEFORE (§8, claude run): grounding = playbook id + compliance status only; Guideline Basis
  could cite nothing but "PB001 + COMP-003 supervisory review at the $50,000 threshold".
- AFTER (claude run 25.8s): the agent retrieves guideline passages for the top
  recommendation via the same `RagGenerationService.retrieve` and the card **quotes the actual
  retrieved document text**; grounding gains `guideline_sources`:
```
guideline_sources: crm_engagement_guide.txt chunk_0001 (sim 0.6402), chunk_0000 (sim 0.5791)
## Guideline Basis
"This guidance rests on playbook PB001 (Pipeline Acceleration) and the CRM Engagement Guide
 (source: crm_engagement_guide.txt) … *'Any activity marked "follow-up required" must carry a
 due date. An overdue follow-up is a coaching signal, not just a task: three or more overdue
 follow-ups on one book correlates with stalled pipeline…'* … Compliance Status: NEEDS_REVIEW
 ([COMP-003]). The estimated $129,600 revenue impact meets materiality ($50,000 threshold)…"
```
The retrieved passage is exactly on-point for A001's real situation (top rec = pipeline
acceleration, 3 overdue follow-ups from the §2-verified snapshot) — semantic retrieval picked
the follow-up-discipline chunk without being told the feature values.

### Housekeeping / honest notes
- `sentence-transformers>=3.0.0` added to pyproject; torch installed CPU-only (codespace has
  no GPU). First model load ~20s per process; cached afterward.
- Environment note: fastapi is at 0.139.0 (lazy `_IncludedRouter` registration — route
  introspection changed, but the live server was verified over HTTP: /adapters/status,
  /knowledge/ask found + not-found paths all serve).
- Verification-induced SQLite/memory mutations reverted; the knowledge catalog re-ingest
  (9 docs / 19 chunks) is the deliverable state and is kept. Chroma dir remains gitignored.
- `LLM_CLIENT_MODE=claude` was inline-env only for the spot checks above; persisted default
  remains mock. `EMBEDDING_CLIENT_MODE` default is `local` (real semantic vectors even in
  otherwise-mock mode — deliberate, per instruction: the mock embedding path is fully replaced).
- Not done (out of 2C-i scope): frontend knowledge page rebuild (2C-ii, awaiting confirmation);
  physical deletion of the dormant runtime-family modules (Phase-11 sweep, unchanged).

---

## 11. Part 2C-ii — Knowledge Hub page + document upload UI (2026-07-04)

Scope: frontend/wiring only. Repoint the Knowledge page off the fake `/ui-integrated`
retrieval onto the real RAG path (`/knowledge/ask` → `RagGenerationService`), and add a real
document-upload UI that drives the same 2C-i ingestion pipeline. **Verified in an actual
headless-Chromium browser session (Playwright), not curl** — a live document uploaded end to end.

### Backend added
- `POST /knowledge/upload` (`app/api/routers/knowledge.py`) — accepts a multipart file
  (PDF/DOCX/PPTX/TXT/MD), saves it under `data/documents/uploads/` (now gitignored), then runs
  the **same** `KnowledgeManagementService.ingest_document` path 2C-i built (real parser → chunk
  → sentence-transformers embed → Chroma → catalog + graph link). Auto-assigns category via the
  existing `_category_for` when not supplied; unsupported suffix → `fail(...)`. Returns
  document_id / document_name / chunks_created / assigned category / status.

### Frontend added / rewired
- `frontend/lib/api/knowledge.ts` — real client: `askKnowledge` (`/knowledge/ask`),
  `listKnowledgeDocuments` (`/knowledge/documents`), `uploadKnowledgeDocument` (multipart
  `/knowledge/upload`). Typed to the RAG response (`found`/`answer`/`sources[]`/`generated_by`/
  `retrieval`).
- `frontend/components/knowledge/knowledge-workspace.tsx` — **rebuilt** as the Knowledge Hub
  (was calling fake `searchKnowledgeIntegrated` → `/ui-integrated/knowledge/search`). Ask box +
  suggestion chips → grounded `AiContentCard` answer (AI-Generated chip) + a cited-sources card
  showing each source's document name, category badge, similarity meter (color-graded) and
  excerpt; honest not-found rendered distinctly. Upload + live corpus list in the side column.
  Built from the Section-1B tokens/patterns (`colors`/`type`/`AiContentCard`), not a generic list.
- `frontend/components/knowledge/document-upload.tsx` — shared real upload widget (file picker +
  category select + result card showing chunks created / assigned category / document id).
- `frontend/components/documents/document-ingestion-workspace.tsx` — **rewired** off the fake
  `ingestKnowledgeDocument` (`/ui-integrated/documents/ingest`) to render the same real
  `DocumentUpload` + indexed-corpus list.

### Browser verification (Playwright, headless Chromium) — live document, end to end

Uploaded a document that does **not** exist in the 9-doc corpus (`orion_liquidity_directive.txt`,
a made-up "Orion Liquidity Directive"), through the real page UI:

```
== /knowledge page ==
Upload result rendered on page:
  Indexed ✓ orion_liquidity_directive.txt — 1 chunk · category Practice Guideline · DOC_dcbc0ec113f0

Asked (typed into the page): "What does an advisor have to file before moving an
  Orion-restricted household into a new managed mandate?"
Grounded answer card cites [1] orion_liquidity_directive.txt (similarity 0.6811) — the
  live-uploaded doc ranks #1, quoting the Orion waiver text back.
Cited sources (5): 1) orion_liquidity_directive.txt 0.681  2) client_review_procedures.txt 0.494 …

Network calls captured to :8000 (the real backend, not /ui-integrated):
  GET  /graph-access/health
  GET  /knowledge/documents
  POST /knowledge/upload      <-- live ingestion
  GET  /knowledge/documents
  POST /knowledge/ask         <-- real RAG

Assertions:
  hit /knowledge/upload : YES
  hit /knowledge/ask    : YES
  hit fake /ui-* path   : no (good)
  answer cites the live-uploaded doc : YES
  OVERALL: PASS
```

Standalone `/document-ingestion` route re-checked the same way: upload renders
`Indexed ✓ … 1 chunk · Practice Guideline`; captured calls = `POST /knowledge/upload` (+ catalog
refresh), **zero `/ui-integrated`**. PASS.

This is the full 2C-ii ask: upload one new document live → it becomes retrievable → a question
that should surface it returns a real grounded answer citing it — proven through real browser
network traffic on the real endpoints.

### Housekeeping / honest notes
- `tsc --noEmit` clean; `npm run build` green (18 routes). Backend imports clean, upload +
  ask verified live over HTTP first, then through the browser.
- Verification-induced mutations reverted: `data/feature_store/iperform_features.db` restored;
  test upload files removed from `data/documents/uploads/` (now gitignored so runtime uploads
  are never committed — the deliverable corpus stays `data/documents/sample_knowledge/`). The
  test docs' Chroma vectors are transient runtime state (Chroma dir already gitignored).
- Working mode: `GRAPH_CLIENT_MODE=mock`, `LLM_CLIENT_MODE=mock` (answer prose is the
  deterministic `[mock-llm …]` draft, but it grounds in the real retrieved passage — swapping to
  `claude` changes only prose, verified in §10), `EMBEDDING_CLIENT_MODE=local` (real 384-dim
  sentence-transformers, so retrieval/similarity are genuine — the 0.681 Orion match is a real
  cosine score).
- Visual QA (Section-1B gate): full-page screenshot compared against the app's design system —
  dark sidebar + light canvas, AI-Generated chip, category badges, color-graded similarity
  meters, dense enterprise type scale. Consistent with the other rebuilt pipeline pages.
- Not done (deferred, unchanged): physical deletion of dormant runtime-family modules and the
  remaining `/ui-integrated` router (Phase-11 sweep). This closes out 2C.

---

## 12. Visual design system audit — 7 pages, pre-Phase-11 (2026-07-04)

All 7 built pages screenshotted at **1440×900 desktop viewport** (full page) via Playwright
(headless Chromium, same tool as the §11 browser verification), then self-audited against
Section 1B. Every value below is a `getComputedStyle` read from the **live rendered DOM**
(scoped to `<main>`), not the intended token — the point was to catch where rendered ≠ intended.

### Screenshots on disk
```
/tmp/claude-1000/-workspaces-ip-demo-project/5a62b380-e96f-41cc-a45a-1a5fe1297a87/scratchpad/audit_screens/
  recommendations.png        (/recommendations)
  features-embeddings.png     (/features-embeddings)
  memory-explainability.png   (/memory-explainability)
  predictions.png             (/predictions)
  advisor-360.png             (/advisor-360)
  knowledge-hub.png           (/knowledge)
  document-ingestion.png      (/document-ingestion)
  badge-info.png              (severity badge — Info state, cropped)
  badge-attention.png         (severity badge — Attention state, cropped)
```
(Scratchpad paths — screenshots are transient verification artifacts, not committed; the
`docs/ui_runtime/screenshots/` repo folder is gitignored by policy.)

### 12.1 Font sizes — labels vs data vs headings (measured px)

| Role | Measured (rendered) | Token intends (`tokens.ts`) | Verdict |
|---|---|---|---|
| Page title `h1` | **22px / w700 / none** (all 7 pages) | `pageTitle` = **20px** | ⚠️ overridden |
| Section title `h2` | **16px / w600** | (no token maps to h2) | from global |
| Card/rec title `h3` | **13px / w600** | `cardTitle` = **14px** | ⚠️ overridden |
| Uppercase labels | **11px / w600 / letter-spacing 0.88px** | `label` = 11px w600 tracking 0.08em (=0.88px) | ✅ exact |
| Category chips | 10px / w600 / ls 0.25px | (chip variant) | intentional smaller chip |
| Table data / values | 12px tabular (td), 13px body | `data` 12px / `body` 13px | ✅ match |

**Root cause of the heading mismatch (headline finding):** `app/globals.css:65-68` carries a
legacy type system from the earlier "Part 15.1 compact" build:
```css
.compact-shell h1 { font-size: 22px; }
.compact-shell h2 { font-size: 16px; }
.compact-shell h3 { font-size: 13px; }
```
`AppShell` wraps the whole app in `.compact-shell` (`app-shell.tsx:30`). `.compact-shell h1`
(CSS specificity 0,1,1) beats Tailwind's arbitrary `text-[20px]` (0,1,0) that `type.pageTitle`
emits — so **every heading takes its size from the compact-shell globals, and the `tokens.ts`
heading sizes (`pageTitle` 20 / `cardTitle` 14) are effectively dead** for `<h1/h2/h3>`.
Font-weight from the tokens survives (globals set no weight) → `h1` still w700, `h3` w600.
Net: rendering is *uniform* across all 7 pages (no per-page drift), but it violates Section 1B's
"token system = single source of truth" — two type systems coexist and the older one wins for
headings.

### 12.2 Icons (lucide-react)

- **Page content (`<main>`): ZERO icons on all 7 pages** — `main.querySelectorAll('svg')` empty
  everywhere; no `lucide-react` import in any of the 7 workspace components.
- **Sidebar only: 17 lucide SVGs** — `lucide-layout-dashboard, chart-line, activity,
  sliders-horizontal, bot, book-open-check, network, git-branch, cloud-upload, shield-check,
  brain-circuit, chevron-left`, etc.
- ⚠️ **Deviation from the 1B composite spec:** the KPI stat card is specified as
  "**icon** + label + value + delta badge" (and `KpiCard` accepts an icon prop), but the rendered
  KPI tiles (`predictions.png`, `advisor-360.png`) are **label + value only — no icon, no delta
  badge**. Clean and consistent, but a narrower card than the blueprint.

### 12.3 Card spacing / padding (measured)

- **Radius: 18px, uniform** across all cards on all pages — correct, `tailwind.config` maps
  `rounded-xl: "18px"`. The legacy `.compact-card` (12px) exists but **no page uses it**
  (grep clean).
- **Padding** (most→least common): `12px 16px` (px-4 py-3, card header/body); `16px` (p-4);
  inner stat tiles `10px` (px-2.5 py-2). Two vertical rhythms (12/16px) coexist — minor.
- Shadow: soft `0 4px 18px rgba(15,23,42,.06)` — consistent subtle elevation.

### 12.4 Severity / status palette — 2-state evidence

`SeverityBadge` renders the `severity` tokens **exactly** (measured rgb → hex):

| State | Measured color | Measured bg | Measured border | Token | Match |
|---|---|---|---|---|---|
| **Info** (`badge-info.png`; predictions, advisor-360) | rgb(29,78,216)=`#1D4ED8` | rgb(239,246,255)=`#EFF6FF` | rgb(191,219,254)=`#BFDBFE` | `severity.info` | ✅ exact |
| **Attention** (`badge-attention.png`; recommendations, memory) | rgb(180,83,9)=`#B45309` | rgb(255,251,235)=`#FFFBEB` | rgb(253,230,138)=`#FDE68A` | `severity.attention` | ✅ exact |

Both cropped screenshots confirm visually (blue INFO pill, amber ATTENTION pill). The
**AI-Generated chip** is likewise consistent: violet `#7C3AED` on `#F5F3FF`/`#DDD6FE`, 10px,
identical on predictions and recommendations.
- **Urgent/Critical not rendered** in these snapshots — advisor A001's data sits in the
  info/attention range; those token entries exist but have no live evidence here.
- ⚠️ **Latent risk:** a *second* status system lives in globals (`.status-good/warn/bad` =
  green/amber/red + `.bg-*-soft`). **None of the 7 pages use it** (grep clean) → no conflict
  today, but it's an unremoved parallel palette a future page could pick up instead of the
  severity tokens.

### 12.5 Table styling (features-embeddings 3×33, advisor-360 4×6)

Measured, **identical on both table pages**:

| Element | Measured |
|---|---|
| `th` | 11px / w600 / **uppercase** / padding `8px 12px` / color `#94A3B8` (muted) / no own border |
| `td` | 12px / w400 / padding `6px 12px` / color `#0F172A` (primary) |
| Row separator | `border-b` on `<tr>`, color `#E2E8F0` (`surface.border`), `last:border-0` |

✅ Matches Section 1B "dense enterprise data-table sizing" precisely: 11px uppercase muted
headers, 12px data rows, tight `py-1.5`/`py-2` padding. Consistent between the two pages.

### 12.6 Bottom line

**Matches 1B:** label typography (11px/0.08em, exact), severity badge palette (exact, 2 states
proven with cropped evidence), AI-Generated chip, table styling (exact + consistent across both
tables), card radius (18px uniform), and — importantly — **strong cross-page consistency**
(nothing drifts page-to-page).

**Does NOT match 1B:**
1. **Heading sizes come from legacy `.compact-shell` globals, not the tokens** — `pageTitle`
   renders 22px (token 20), `cardTitle` renders 13px (token 14). Two type systems coexist; the
   global wins by specificity. Clearest violation of "tokens = single source of truth."
2. **KPI cards omit the icon + delta badge** the 1B composite spec calls for (label + value only).
3. **A second, unused status palette** (`.status-*` / `.bg-*-soft`) still lives in globals —
   dormant on these pages but a latent inconsistency.

None of these are per-page drift or fake data — they are residue of the earlier "compact-shell"
build layered under the newer token system. Cleanest fix for #1: delete the
`.compact-shell h1/h2/h3` rules (let the token classes take effect) or reconcile the token values
to 22/16/13. Deferred to the Phase-11 sweep (not changed here, per the "confirm before Phase 11"
hold).

---

## 13. Chart-type conformance — 3 pipeline pages get real data visualizations (2026-07-04)

Per the new Section-1B "visualization-type rule": data whose mockup concept is a chart must be
rendered as that chart, backed by real API computation, not a number/table. Three pipeline pages
got real Recharts visualizations. The dataviz skill was loaded first; every multi-series palette
was run through its validator. Working mode `GRAPH_CLIENT_MODE=mock` (109,328 rows),
`EMBEDDING_CLIENT_MODE=local`. Charts render live in a headless-Chromium capture (not mocked).

### Palettes validated (dataviz `validate_palette.js`, light surface)
```
donut 4-cat  #2563EB,#14B8A6,#7C3AED,#F59E0B      -> ALL CHECKS PASS
impact 3-ser #14B8A6,#2563EB,#DC2626              -> ALL CHECKS PASS
scatter pair #2563EB(target),#F59E0B(similar)     -> PASS (CVD ΔE 141.8; blue+violet FAILED
              deutan ΔE 1.7 and was rejected — amber chosen instead). "other" = neutral gray
              background (intentional de-emphasis + smaller marker, not a competing category).
```
Contrast WARNs (teal/amber < 3:1) are satisfied by the required relief: legends + direct value
labels + adjacent table/list on every chart.

### 1. Advisor 360 — revenue trend line + account-mix donut

- **Backend:** `/advisor/360/{id}` extended with `revenue_trend` (GQ-005
  `get_revenue_trend_by_scope`, period_grain=MONTH — the SAME data the Revenue Agent reads) and
  `account_mix` (graph accounts aggregated by `account_type`, real `current_value`).
- **Real data proof (A001):**
  ```
  revenue_trend: 24 months  first {Aug 2024, $28,997.49, 7 txns} … last {Jul 2026, $31,429.17}
  account_mix: BROKERAGE $464,765 (3) · MANAGED $451,699 (3) · TRUST $380,263 (3) · IRA $369,572 (3)
  ```
- **Line chart** shows the real 24-month movement (non-zero y-baseline fitted to the data range so
  month-to-month change is visible; tooltip carries absolute $ + txn count). **Donut** = book
  composition by account type (28/27/23/22%), legend + $ values + %.
- **Honest substitution:** the ask was a *household-segment* donut, but A001's 6 households are
  **all `AFFLUENT`** (monoculture in the seed) — a 1-slice donut violates the dataviz "is it even
  a chart" rule, so account-type composition (real, varied) is the meaningful breakdown. Segment
  data does exist; it just doesn't vary, so it stays in the households table (where the mockup
  puts it) rather than a fake pie.

### 2. Feature/Embeddings — real PCA 2D projection scatter

- **Backend:** `/embeddings/projection/{id}` — loads all persisted advisor embedding vectors
  (SQLite `embeddings`, 8-dim deterministic feature-projection, **60 real vectors**), runs
  **sklearn `PCA(n_components=2)`** (real dimensionality reduction, no fabricated coordinates),
  role-tags the target advisor + its top-k cosine-similar peers.
- **Real data proof (A001):**
  ```
  reduction: PCA · source_dimensions: 8 · point_count: 60
  explained_variance_ratio: [0.5754, 0.1391]   (PC1 57.5%, PC2 13.9% — real variance)
  roles: {target: 1, similar: 5, other: 54}
  target A001 at (-0.6945, -0.4081); similar A004 0.858 / A007 0.844 / A003 0.831 …
  ```
- **Scatter** renders 60 points: target = large blue, 5 similar = amber (size + hue = secondary
  encoding), 54 others = small faded gray. The screenshot shows the **similar advisors genuinely
  cluster around the target** in the projection — the reduction and the embedding agree, which is
  itself evidence the vectors are real. The similar-advisors list sits in the adjacent panel with
  matching amber dots and the same cosine scores.

### 3. Recommendations — recommendation-impact-over-sequence line

- **Backend:** `/feedback-learning/impact-trend` — replays the REAL feedback loop over the REAL
  recommendations of a 6-advisor cohort (`RecommendationService.generate_for_advisor`,
  `persist=False`), each action derived deterministically from the rec's own attributes
  (URGENT/CRITICAL→COMPLETE, conf≥0.85→ACCEPT, conf<0.75→REJECT, else MODIFY), accumulated with
  the real `ACTION_SIGNALS` reward table and the same clamped weight update the live loop uses.
  **Pure computation — no persistence, no side effects.**
- **Honest framing (important):** the live feedback loop writes to the graph with a **fixed
  `as_of` date** and persists only `learning_weights` — the build has **no calendar-time feedback
  history by design**; the loop's effect is observable along the feedback *sequence* (exactly what
  §2/§6 verified: "3× COMPLETE → 0.84→0.94→1.04→1.14"). So the x-axis is the **feedback round**,
  not an invented calendar date. No placeholder trend lines.
- **Real data proof:**
  ```
  16 events over 6 advisors' real recs
  accepted 0→8, implemented 0→2, rejected 0→6 ; net reward 3.8 ; captured impact $1,435,424
  final weights: CRM_EXECUTION 1.50 (10 events, up)  MANAGED_MIX 0.53 (6 events, down)
  ```
  The MANAGED_MIX (0.71-confidence product-push) recs are rejected → its weight falls to 0.53
  while CRM_EXECUTION rises to the 1.5 cap — the **§2-verified both-directions learning behavior**,
  now shown as a chart. Three stepped lines with a legend; the weight badges below tie it to the
  live learning state.

### Rendering verification (headless Chromium, real DOM)
```
advisor-360:         2 recharts surfaces; revenue line-curve height 124px (real oscillation),
                     donut 4 slices
features-embeddings: scatter 60 pts (1 target blue, 5 similar amber, 54 gray), PCA note PC1 58%/PC2 14%
recommendations:     3 line-curves present — #14B8A6 h177, #DC2626 h111, #2563EB h44 (real rises)
```
Fix applied mid-verification: Recharts line-draw animation left lines mid-draw at capture time →
set `isAnimationActive={false}` on all line series (the scatter already had it); revenue-trend
y-axis switched from 0-baseline (which flattened the $28-38K band into a top sliver) to a
data-fitted non-zero baseline. `tsc` clean; `npm run build` green (21 routes).

### Screenshots
```
/tmp/claude-1000/.../scratchpad/audit_screens/chart-advisor-360.png
/tmp/claude-1000/.../scratchpad/audit_screens/chart-features-embeddings.png
/tmp/claude-1000/.../scratchpad/audit_screens/chart-recommendations.png
```

### CLAUDE.md
Section 1B gained the **Visualization-type rule** (concept→form mapping; chart real data with
tokens; table/list only where the mockup uses one; don't chart non-charts) — a standing
requirement for the chart-dense Phase-11 pages.

**New chart components** (token-based, distinct from the older `charts/revenue-trend-chart.tsx`
used by the out-of-scope exec dashboard): `charts/advisor-revenue-trend.tsx`,
`charts/account-mix-donut.tsx`, `charts/embedding-scatter.tsx`, `charts/impact-trend-chart.tsx`.
Not done (unchanged): Phase-11 breadth pages; dormant runtime-module deletion.
