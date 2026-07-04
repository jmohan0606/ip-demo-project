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
