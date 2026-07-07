# STATUS_CHECK — Master Execution Run (Sections 12 → 13 → 13B → 10 → 14)

_Started: 2026-07-06. Main thread: Opus 4.8. Design delegations: `fable-architect` / general-purpose subagent with `model:"fable"`._

---

## Session 12 — architecture audit + persona/UX fixes (4 items) (2026-07-07)

Real Claude available (`LLM_CLIENT_MODE=claude`). Committed per item; backend boots (46 routes);
frontend tsc PASS throughout.

| # | Item | Status | Key evidence |
|---|------|--------|--------------|
| 1 | TigerGraph-vs-SQLite state audit (investigate only) | **Done — no code change** | New `DATABASES.md`. Verdict: **genuine architectural divergence**, not a config-swap. All durable state (learning weights, rec status, impact ledger, 6 memory types) is in **SQLite via hardcoded `SQLiteManager()`/raw `sqlite3`** — no persistence adapter (`BaseRepository` is an empty stub). `GraphClient` IS a real adapter but graph writes are best-effort ephemeral mirrors (`replay_on_boot` rehydrates the ledger). Schema HAS most types (conversation/reasoning/context-memory, feedback/outcome/learning + edges, seeded) but LACKS impact-ledger + rec-status-transition vertices; procedural memory unpopulated. Documented both SQLite DBs + confirmed both DBs + Chroma gitignored & auto-recreated. Includes a concrete 6-step path to make TG the authority. |
| 2 | DDW ≠ MDW: fix DDW text + build MDW market journey | **Done** | DDW (Division) and MDW (Market) separated; division journey → "Division-Leader Journey (DDW)". New MDW MARKET journey reconciles: **Market M01 (Boston Metro) $3,713,409 → $3,760,462 = +$47,053.23**; 3 tasks persisted; 5 real AI drivers (conf 0.82). Browser: MDW persona, breadcrumb Market: Boston Metro, Step 1/9, green proof bar names real lagging advisors. `mdw_step1.png`. |
| 3 | ID + Name everywhere (shared helper) | **Done** | `GET /hierarchy/entity-names` (466 names) + `formatEntity()` + `useEntityLabel()` hook (module-cached). Applied to exec dashboard header/evidence/AI-title/advisor tables, shared AdvisorSelector, Advisor 360, Predictions. Header now **"F001 · Chase Wealth Management Overview"**, tables "A001 · Avery Diaz". `item3_id_name_dashboard.png`. |
| 4 | Consistent header type hierarchy (shared tokens) | **Done** | Canonical `type.eyebrow` < `pageSubtitle` < `pageTitle` (22px) tokens + shared `PageHeader` component. Applied to exec dashboard (eyebrow→title→subtitle→PDF/PPT actions); swept **15** other workspaces' ad-hoc `text-[22px] font-black` onto `type.pageTitle`. `item4_header_hierarchy.png`. |

Commits: `002a13f` (item 1) · `efaf11d` (item 2) · `f8137f4` (item 3) · `736bc61` (item 4).
(The prompt said "five items" but listed four; flagged in the handoff.) Screenshots under
`docs/qa_screenshots/session12/` (gitignored). Item 1 is investigation + a recommended path in
`DATABASES.md` — no code changed, for a joint decision on the TigerGraph-as-authority refactor.

---

## Session 11 — all 6 remaining deferred items COMPLETE (2026-07-07)

Real Claude available all session (`LLM_CLIENT_MODE=claude`, verified). Committed per item;
frontend tsc PASS throughout; backend boots (46 top-level routes, new endpoints live HTTP 200).

| # | Item | Status | Key evidence |
|---|------|--------|--------------|
| 1 | AI-Generated labeling correction | **Done (audit)** | Per-card chip already literal "✦ AI Generated" (no product name); AI Assistant already "iPerform Coach Q&A Assistant" (8bb6380) — confirmed, no reverts needed. Added shared `ProductSystemLabel` proactive tag on predictions/recommendations/advisor-360. `predictions_label.png`. |
| 2 | 13B.3 division-leader guided journey | **Done** | 9-step DIVISION_STEPS in the existing story engine (no new backend). Real spine reconciles: **D01 $14,738,198 → $14,785,251 = +$47,053.23** (= completed rec impact); 3 coaching tasks persisted; AI insight 5 real drivers (conf 0.82). Browser: DDW persona, Eastern Division, Step 1/9, green proof bar names real lagging advisors. `story_div_step1.png`. |
| 3 | AUM net-flows waterfall (Exec Dashboard) | **Done** | `AumNetFlowsService` + `GET /scope/aum-net-flows`: reconciling bridge from real monthly AUM/NNM + FEE txns. **FIRM $2.065B +20.4M −1.26M +23.5M −10.2M = $2.098B** (fees 0.49% of AUM); DIVISION scoped. `dashboard_aum_waterfall.png`. |
| 4 | Export dashboard to PDF/PPT | **Done** | `dashboard_export.py` (reportlab + python-pptx) renders the real rollup; `GET /export/dashboard?format=pdf\|pptx` + exec buttons. Valid PDF (real $35.89M/$2.09B extracted) + PPTX; Playwright click → real browser download. `export_buttons.png`. |
| 5 | Household model extensions | **Done** | Household churn already existed (household-churn-xgb) — confirmed. NEW next-best-product propensity reusing the model tier (registry + ModelClient + `/predictions/next-best-product/{advisor}`): collaborative propensity over the real holdings graph. A001→H0001 top "Alternatives" 0.68 (68% AFFLUENT peers); held∩recommended=∅; A005 different households. |
| 6 | AI-Assistant completion narration | **Done (real Claude)** | Strengthened `context_assembler` (always narrate measured impact + explicit completion summary). Before/after: A012 BEFORE "no record of a recently completed initiative"; AFTER a "What Was Completed / Measured Financial Impact" section + LTM $454K→$685K (= +$231,400 impact). `item6_narration_before_after.txt`. |

Commits: `e77fd3c` (item 5 + item 1 labels) · `29ee2fa` (item 3) · `cb0834e` (item 4) ·
`7e80d63` (item 2) · `aae4b30` (item 6). Nothing was faked or deferred; where an item was
already satisfied (household churn, the chip/rename), that was confirmed with evidence rather
than rebuilt. Screenshots/transcripts under `docs/qa_screenshots/session11/` (gitignored).

---

## Pre-migration data audit — is every change in the committed CSVs? (2026-07-06)

**Ask:** the client rebuilds their entire TigerGraph from the committed
`docs/tigergraph_foundation/data/sample/*.csv` + `manifest.json` — nothing else. Verify every
data change across all sessions is materialized in those CSVs, not runtime-only. Definitive test:
would a from-CSV-only rebuild reproduce what the app shows?

### VERDICT: YES — a CSV-only rebuild reproduces current app state. No gaps to export.

**Re-confirmed 2026-07-07 (names are literal CSV values, not load-time-generated):** read the raw
committed files directly — `phx_dm_firm.csv` → `F001,Chase Wealth Management,NWM,ACTIVE`;
`phx_dm_division.csv` → `D01,Eastern Division,…`; `phx_dm_household.csv` → `H0001,The Whitfield
Family,…`; `phx_dm_branch.csv` → `B001,Back Bay Office,…`; `phx_dm_advisor.csv` → `A001,Avery
Diaz,…`. The load path does **no** name generation: `foundation_store.py:62` sets
`attrs = {graph_attr: _coerce(row.get(src)) …}` — values come straight from the CSV cells
(`_coerce` only casts type), and the real RESTPP/pyTigerGraph loaders upsert those same cell
values. Placeholder grep (`Household [0-9]`, `Division [0-9]`, `Northwestern Mutual`, `Firm [0-9]`,
…) across all vertex+edge CSVs = **0 hits**. So a graph from ONLY the CSVs yields the real names,
never "Household 1"/"Division 1"/an old firm name. Name-generation is not needed at load time.

**Definitive empirical test (not a claim):** moved the two gitignored runtime SQLite DBs
(`data/feature_store/iperform_features.db`, `data/sqlite/iperform.db`) aside to simulate a fresh
client clone (CSVs only, empty SQLite), booted the app in mock mode (graph loaded purely from the
foundation CSVs), and probed every key page. All reproduced real data from the CSV-seeded graph:
- `/scope/dashboard FIRM` → $35.9M rollup · `/revenue/analytics FIRM` → $109.3M, 15,116 txns, 60 advisors
- `/advisor/360/A001` → "Avery Diaz" · `/recommendations/advisor/A001` → REC_A001
- `/predictions/revenue-decline/A001` → real prediction · `/coaching/advisor/A001` → real sessions
- `/feedback-learning/outcome-learning` → **events_used: 180** (matches the 180 feedback CSV rows)
Then restored both DBs (verified back to 8.8 MB / 4.3 MB).

### Item-by-item (each confirmed present in CSV + manifest)
| Item | Result |
|---|---|
| **Firm = "Chase Wealth Management"** | ✅ `phx_dm_firm.csv`: `F001,Chase Wealth Management,NWM,ACTIVE` — in the data, not just a UI label |
| **Expanded date range** | ✅ `phx_dm_revenue_transaction.csv` spans **2023-08 → 2026-07** (15,116 rows, 1,038 distinct dates); 36 time periods; monthly AUM/NCF/NNM series present |
| **Real-world entity names** | ✅ households "The Whitfield Family"…, divisions "Eastern/Central/Western", regions, markets "Boston Metro"…, branches "Back Bay Office"…, advisors "Avery Diaz"… — zero "Household 1" placeholders |
| **Outcome variety (feedback loop)** | ✅ `phx_dm_feedback_event.csv` 180 rows mixed (ACCEPT 36 / REJECT 39 / COMPLETE 73 / IGNORE 14 / DEFER 7 / NOT_RELEVANT 7 / MODIFY 4); `phx_dm_outcome_event.csv` 180 (REVENUE_IMPACT 134 / ACTION_TAKEN 46); `phx_dm_recommendation.csv` 120 across all 5 statuses |
| **New `coaching_task` vertex + edges** | ✅ `phx_dm_coaching_task.csv` (90 rows, real manager-assigned tasks) + edges `coaching_task_for_advisor`, `coaching_task_assigned_by` — all in manifest. Schema grew 56→**57 vertices**, 126→**128 edges** vs the original baseline; also notification/guardrail/evaluation types present |
| **Recommendation / feedback data** | ✅ recommendation, feedback_event, outcome_event, learning_signal, opportunity, prediction_result, feature_snapshot, embedding, similarity_match all seeded as CSV vertices |

### Structural integrity
- **Manifest ↔ CSV: perfectly consistent** — 185 entries, 0 missing CSVs, 0 row-count mismatches,
  0 CSVs-on-disk-not-in-manifest.
- **Foundation validator: STATUS PASS** — 57 vertices / 128 edges / 128 reverse edges / 185 files
  / 155,954 data rows / 43 queries; every edge FROM/TO resolves.
- **Working tree == committed** — no uncommitted CSV/manifest changes; nothing regenerated-but-unpushed.

### Runtime-only stores — checked, nothing lost
- The two SQLite DBs are **gitignored** (`data/*/*.db`) — they never travel to the client; only
  the CSVs do. The reproduction test above proves the app doesn't need them: graph-data pages read
  from the graph and derive/regenerate into a fresh SQLite on demand.
- **Section-13 lifecycle** (`phx_dm_local_impact_ledger`, `phx_dm_local_rec_status_transition`) are
  SQLite-only types with **no CSV/vertex** — but both hold **0 rows** right now, so there is
  nothing to export. (These are per-session demo state; on the rebuilt graph the app regenerates a
  completion's impact fresh when a recommendation is completed — `replay_on_boot` reinjects from
  the ledger, which is currently empty.) **If** the client wants a pre-completed lifecycle demo to
  survive migration, that would need exporting then — there is none to export today.

### Honest caveat (not a CSV/graph gap)
- Trained ML artifacts (`models/artifacts/*.joblib`, `*.pt`: GraphSAGE, XGBoost churn/AGP,
  IsolationForest) are **gitignored by design** — only `models/registry.json` (metrics/metadata)
  is committed. A fresh clone regenerates them via `scripts/train/*` or falls back to
  `MODEL_CLIENT_MODE=deterministic`. This is model state, not graph data — out of the CSV-migration
  scope — but flagged so the client knows to run training (or accept deterministic scoring) after
  the graph rebuild.

**Bottom line:** nothing was found living only in runtime SQLite/mock/in-memory that needs
exporting. The committed CSVs + manifest are a complete, self-consistent source of truth; a
from-CSV graph rebuild reproduces the current app state, proven empirically.

---

## Real-remote TigerGraph: step logging + token(getToken)/SSL + .env (2026-07-06)

**Ask:** make the ingestion screen's real-remote path fully diagnosable from `logs/app.log` on
its first run against the client's real remote (AWS) TigerGraph, and confirm it handles a
token-secured + SSL connection with all properties configurable in `.env`.

### Structured step-logging added (logger `app.graph.tigergraph`, uses the new logging system)
Both real tiers now emit a clear step trace to `logs/app.log`:
- **Tier 2 pyTigerGraph** (`app/graph/tiered_client.py`): `connecting` (host, graph, ports,
  use_ssl, verify_ssl, auth mode, masked secret) → `token acquired via getToken(secret)` →
  `connection established (echo ok)` → `vertex/edge batch upserted` (type, requested, accepted)
  → on any failure, `connection FAILED`/`upsert PARTIAL` with the **full stack trace**.
- **Tier 3 RESTPP** (`app/graph/client.py` `RealGraphClient`): `client initialized` →
  `token acquired via requesttoken(secret)` → `connection established (echo ok)` →
  `%s batch upserted` (kind, target, requested, accepted) → `upsert rejected/PARTIAL` +
  token-acquisition failure, all with full error.
Secrets/tokens are always masked in logs (`<set:N chars, …last4>`) — never printed in plaintext.

### Token (getToken) + SSL — now actually wired (was a real gap)
- **Before:** `tigergraph_secret` existed in settings but was **never used**; no getToken flow
  anywhere. A secured instance with only a secret would have failed to authenticate.
- **Now:** auth precedence **JWT → static API token → getToken(secret) → user/pass**.
  - Tier 2 calls `conn.getToken(secret[, lifetime])`.
  - Tier 3 (httpx RESTPP) requests a token via `GET /restpp/requesttoken?secret=…` and sets it
    as `Authorization: Bearer …` on subsequent calls.
  - SSL: `TG_USE_SSL=true` forces the `https://` scheme (Tier 2 + Tier 3); `TG_VERIFY_SSL`
    honored (Tier 2 sets pyTigerGraph verify flags when false for self-signed; Tier 3 passes
    `verify=` to httpx). `TG_SSL_PORT` passed to pyTigerGraph.

### `.env` completeness — added the missing/dead keys
`.env.example` documented `TG_SECRET`/`TG_JWT_TOKEN`/`TG_SSL_PORT` but **settings.py never loaded
them** (dead vars). Added real fields: `TG_SECRET`, `TG_JWT_TOKEN`, `TG_SSL_PORT`, `TG_USE_SSL`,
`TG_VERIFY_SSL`, `TG_TOKEN_LIFETIME_SECONDS` (all `TG_*` aliased). RESTPP tier reuses
`TIGERGRAPH_SECRET`/`TIGERGRAPH_TOKEN`/`TIGERGRAPH_VERIFY_SSL` (already present). `.env.example`
updated with an AWS-remote how-to comment block.

### Verified (real evidence, stub servers)
- **RESTPP token flow:** secret set, no static token → client made `GET /restpp/requesttoken?
  secret=…` then `POST /restpp/graph/g1` with `Authorization: Bearer TOKEN_…`; logs showed
  `initialized (auth=secret->requesttoken)` → `token acquired (…3XYZ)` → `vertex batch upserted
  accepted=1/requested=1`. Secret masked.
- **pyTigerGraph SSL + getToken + failure:** `TG_USE_SSL=true` rewrote bare host to
  `https://…` (ssl_port 443, verify_ssl honored); logs showed `connecting (auth=secret->getToken,
  use_ssl=true, secret=<set:14…-xyz>)` → `connection FAILED: ConnectionError` **with full trace**
  (the exact first-run diagnosability the client needs).
- **No regression:** app imports (45 routes); new settings load; mock ingestion still persists
  (60→61, `A_REG_1` present).

### To point at the client's real remote
`GRAPH_CLIENT_MODE=real`, `TG_HOST=https://<aws-host>`, `TG_USE_SSL=true`, `TG_GRAPHNAME=…`, and
one of `TG_JWT_TOKEN` / `TG_API_TOKEN` / `TG_SECRET`. First run's every step (and any failure)
lands in `logs/app.log`.

---

## Data Ingestion end-to-end trace + real-remote RESTPP fix (2026-07-06)

**Ask:** verify the Data Ingestion screen (the client's ONLY path to load CSVs into a remote
TigerGraph, since they can't use GraphStudio file-path loading) works end-to-end, and confirm it
uses a REST/upsert path needing NO server-side file. Plus: auto-create `logs/` on startup.

### How ingestion actually loads data (traced)
UI (`data-ingestion-workspace.tsx`) → pick an entity → **Run Ingestion** → `POST /ingestion/run`
→ `IngestionService.run_entity_ingestion` reads the bundled foundation CSV
(`docs/tigergraph_foundation/data/sample/vertices/<file>`) → header + per-row validation →
delta-detect (hash) → **per-row vertex upsert** via `TigerGraphUpsertClient`. (The screen loads
vertices only; it does not upload a user file — it ingests the bundled verified dataset by name.)

### Two real defects found (diagnosed, both = original never-closed gaps, not Section-11 regressions)
1. **Real-remote REST path was broken.** `TigerGraphUpsertClient` routed through a *second,
   parallel* `GraphAccessClient` whose REST upsert did `POST graph/{graph}/vertices/{type}` with
   body `{vertex_type, primary_key, attributes}` — **not a valid RESTPP endpoint or payload**.
   Against a real remote TigerGraph it would 404/400. (The correct RESTPP upsert already existed
   in the canonical `RealGraphClient` but ingestion wasn't using it — the classic two-parallel-
   implementations trap.)
2. **Mock upsert was a silent no-op.** The fallback `MockGraphDataService.upsert_vertex` just
   returned `{"success": true}` and persisted nothing. **Proven:** store held 60 advisors before
   AND after upserting `A_TEST_999`; the row never appeared — yet the UI reported success. So in
   the current default (`GRAPH_CLIENT_MODE=real`, no reachable engine) every "created/updated"
   count was fictional.

### Fix
Rerouted `TigerGraphUpsertClient` (vertex + edge) through the canonical `get_graph_client()`
adapter, building the proper manifest-driven `entry` (schema `id_column`, edge
`from_type`/`to_type` from `docs/tigergraph_foundation/data/manifest.json`). One path now serves
every mode:
- `real`/`local_real` → TieredGraphClient: pyTigerGraph `upsertVertices`/`upsertEdges` (Tier 2)
  or RESTPP `POST /graph/{graph}` JSON upsert (Tier 3) — **schema-driven, no server-side file**.
- `mock` / Tier-4 fallback → MockGraphClient, which **persists into the same FoundationGraphStore
  the read queries traverse**, so rows are immediately visible to the app.
Primary key is carried as the vertex id and excluded from attributes (matching the verified
foundation loader). Also benefits the two other callers (opportunity + feedback linkers).

### Verified (real evidence)
- **Rows now land (mock):** store 60 → **61** advisors after upserting `A_TEST_999`; queryable
  with correct attrs `{advisor_name, status}` (PK correctly not an attribute). `accepted_vertices=1`.
- **Real-remote RESTPP is correct:** pointed `RealGraphClient` at a local stub and captured the
  actual request → `POST /restpp/graph/iperform_demo` body
  `{"vertices":{"phx_dm_advisor":{"A_REMOTE_1":{"advisor_name":{"value":"Remote Advisor"},"status":{"value":"active"}}}}}`
  — file-less RESTPP JSON upsert, PK as the vertex key. ✅
- **HTTP path works:** `POST /ingestion/run {account}` → 200, 5 processed, 0 failed. The one
  logged ERROR is the *expected* Tier-3 `Connection refused` (no live engine here), after which
  it fell back to the persisting mock — designed behavior (and it validates the new adapter
  logging too).
- **Linker edges/vertices resolve** from the manifest (e.g. `phx_dm_opportunity_for_advisor →
  phx_dm_opportunity → phx_dm_advisor`).

### Honest status for the client
- Against **mock / no-engine**: works and genuinely persists (queryable) — no more fake counts.
- Against a **real remote TigerGraph**: now uses the correct file-less RESTPP/pyTigerGraph
  upsert. Not executed against a live remote from here (none reachable), but the exact outbound
  request was captured and confirmed valid. Set `GRAPH_CLIENT_MODE=real` + `TIGERGRAPH_RESTPP_URL`
  (+ token) to the remote instance and it will POST straight to `/graph/{graph}`.
- **Not built (flagged, out of current scope):** the screen still ingests bundled CSVs by name;
  there is no arbitrary user-file *upload* control. If the client needs to upload their own CSVs
  (not just the shipped dataset), that upload endpoint + UI control is a follow-up.

### logs/ auto-create (item 1)
Added `self.log_dir` to `Settings.ensure_local_directories()` (runs at `get_settings()`), on top
of the existing lazy `mkdir` in the file handler. Verified: deleted `logs/`, loaded settings →
`logs/` recreated. A fresh environment can't error writing the first log line.

---

## Structured logging & error handling — CloudWatch-ready backend (2026-07-06)

Added production-grade, ECS/CloudWatch-ready observability to the FastAPI backend. Replaced the
loguru-stderr-only setup with stdlib `logging` emitting single-line JSON events.

**What was built**
- `app/shared/logging.py` — `JsonFormatter` (timestamp, level, logger, correlation_id, message,
  source, promoted `extra=` fields, and full `exception.{type,message,stack_trace}` on errors) +
  `configure_logging()` with a **swappable sink via `LOG_SINK`**: `file` (RotatingFileHandler →
  `logs/app.log`, 10 MB × 5 backups, local default) · `stdout` (same JSON to stdout — the
  Fargate→CloudWatch path) · `cloudwatch` (watchtower handler, safe stdout fallback if the pkg/
  creds are missing). Both documented in the module docstring so switching is a config change,
  not a rewrite. Routes uvicorn/fastapi loggers through the same handler.
- `app/shared/correlation.py` + `app/api/middleware/correlation.py` — contextvar-based
  correlation id; middleware reuses inbound `X-Correlation-ID`/`X-Request-ID` or mints one,
  binds it to every log line for the request, echoes it back on the response header, and logs
  request start/complete/failed with method/path/status/duration.
- `app/api/middleware/error_handlers.py` — global handlers now log full traces (`exc_info=True`)
  and return a clean structured envelope `{success,error,message,correlation_id}` — never a raw
  stack to the user. Generic `Exception` → 500 "Unexpected server error".
- `app/shared/adapter_logging.py` — `@logged_adapter_call("graph"|"llm")` applied to
  GraphClient `run_query`/`upsert` (Real+Mock) and all three LLMClient `generate` methods: on
  failure logs component/operation/redacted-args/error_type + trace, then re-raises so the API
  boundary returns the clean error.
- `app/api/routers/diagnostics.py` — `/_diagnostics/{ping,boom,handled-error}` (gated by
  `ENABLE_DIAGNOSTICS_ROUTES`, off in prod) for verifying the log pipeline.
- Settings + `pyproject.toml` optional `aws` extra (`watchtower`, `boto3`).

**Verified (real evidence, port 8011, mock mode)**
- `GET /_diagnostics/boom` with `X-Correlation-ID: test-trace-123` → client got clean
  `{"success":false,"error":"internal_error","message":"Unexpected server error",
  "correlation_id":"test-trace-123"}` HTTP 500 (no stack leaked).
- `logs/app.log` captured the matching ERROR JSON records (`app.request` + `app.api`) with
  `exception.type=RuntimeError`, full `stack_trace`, and `correlation_id=test-trace-123`.
- Adapter decorator fired on a bad query: `app.adapter` record with
  `adapter_component=graph, adapter_operation=run_query, adapter_args=['NO_SUCH_QUERY_XYZ',
  "<dict keys=['advisor_id']>"]`, full trace, and re-raised (404 to client).
- `LOG_SINK=stdout` emitted valid JSON to stdout with `extra` fields promoted (ECS path).
- Response `X-Correlation-ID` header present on normal requests. App imports clean (45 routes).

**Deferred / notes:** `watchtower`/`boto3` are lazy-imported optional deps (only for
`LOG_SINK=cloudwatch`); `LOG_SINK=stdout` needs neither. `*.log` already gitignored.

---

## 13B.3 Division-Leader Guided Journey — remaining-work assessment (2026-07-06)

**Verdict: it is the guided-overlay wrapper only — NO backend is missing.** Every capability the
division journey needs already exists and was probed live and returns real data:
- Division rollup: `GET /scope/dashboard?scope_type=DIVISION&scope_id=D01` → real totals (rev_ltm
  $14,738,198) + `bottom_advisors` with stated reasons (Avery Diaz "lowest LTM revenue", Jordan
  Garcia "AGP attention (risk 56.6)"). ✅ (built §12.1)
- Division-scope AI insight: `GET /scope/ai-insight?scope_type=DIVISION` → 200, grounded prose. ✅
- **Scope-aware rollup reasoning (§11.6) works**: `POST /ai-chat/ask` with `scope_type=Division,
  persona=DDW` → 200; the §11.6 ScopeRollupService path was already verified with real Claude
  ("Division D01 'why is revenue lagging' reasons across 24 advisors, names Top + Needs-attention,
  not one advisor"). So the DDW "which of my advisors need attention?" step is real, not a stub.
- Coaching-task CRUD (§9.5): `GET /coaching/task-catalog` 200 + `POST /coaching/tasks` exist —
  the manager-assigns-a-task step is a real persisted write, retrievable as AI context. ✅
- Division-level propagation: division `totals.revenue_ltm = Σ advisor snapshots`, so completing a
  rec for a contributing advisor moves the division rollup by exactly the impact — the SAME §13.3
  math already verified to the cent at firm level. No new code; it holds by construction.

**What's actually left to build (all frontend, ~80–120 lines, no new backend):**
1. A second `Scenario` entry (~7 steps) in `frontend/components/story/scenarios.ts` — the story-launch
   page already `.map`s SCENARIOS, so a second card auto-appears. Steps: division view → who-needs-
   attention (real `bottom_advisors`) → drill into that advisor → assign a coaching task (real
   `POST /coaching/tasks` as a story `action`) → accept+complete the advisor's top rec (reuses the
   existing action machinery verbatim) → division rollup moved (before/after proof) → ask as the leader.
2. Provider: derive the division `{D}` from the chosen advisor at launch (today `start()` passes a
   hardcoded "D01") — resolve via the already-loaded hierarchy tree, ~15 lines; set persona DDW
   (`shell.setPersona("DDW")` — the mechanism already exists).
3. Two `data-story-target` attributes: `bottom-advisors-table` on the Executive Dashboard and one on
   the coaching-reviews task area (attribute-only edits).
4. One new story `action` shape: POST a task from `/coaching/task-catalog` (the overlay's action
   runner already does POST calls — just a new call spec).
5. Verification: a Playwright pass through the ~7 stops + assert the division rollup before/after
   differs by exactly the impact (same assertion style as `verify_section13B_story.py`).

**Effort: ~1.5–2.5 focused hours; risk LOW.** The only genuinely-new wiring is the coaching-task
story-action and the advisor→division resolution at launch. All reasoning, rollups, propagation, and
coaching persistence are done and verified. It was deferred purely for session length, not difficulty.

## Master Execution Order (from CLAUDE.md §12 header) — CONFIRMED

Follow EXACTLY, no reordering:

1. **Section 12 — Regression Audit & Critical Fixes.** Fix the broken foundation first: filter
   bars, Executive Dashboard missing components, Revenue Analytics (real geographic map), Advisor
   360 centrality clarity + accounts/segment split, CRM funnel redesign, explicit advisor-selector
   dropdowns on the 4 pipeline pages, Feature Lab re-verify post-§11, Opportunities visible-feedback
   minimum, Admin Health/Observability Next.js errors, nav/branding (rename Firm → **Chase Wealth
   Management** in seed data, not just a label).
2. **Section 13 — End-to-End Stateful Recommendation Lifecycle.** Real state machine
   (OPEN→ACCEPTED→IN_PROGRESS→COMPLETED / REJECTED / IGNORED / MODIFIED), persisted transitions with
   timestamp+actor, terminal-status button disabling, real simulated impact ledger on completion
   (linked by edge to the recommendation), cross-screen propagation, AI Assistant awareness,
   regeneration cycle, explainability retained. Design delegated to `fable-architect`.
3. **Section 13B — Guided End-to-End Story Mode.** The NARRATION layer built ON TOP of §13's real
   loop: a "How It Works" pipeline-trace view (Data→Features→Model→Opportunity/Rec→Context/
   Compliance→Output with real artifacts + timing), a replayable 10-step flagship guided scenario
   driving the REAL app on REAL data, a rollup-persona (DDW/MDW) journey, and a business-impact/ROI
   summary from real recorded outcomes. Design delegated to `fable-architect`.
4. **Section 10 — Remaining items only.** Household-level model extensions, AGP cohort/mentor/ROI,
   real search/notification icons, AUM net-flows waterfall, PDF/PPT export — re-check each against
   what §11–13B already built; build only the genuinely-unsatisfied ones. `fable-architect` only for
   AGP-ROI methodology + mentor-matching algorithm.
5. **Section 14 — Final directive.** Flip running config to real graph + real LLM
   (`GRAPH_CLIENT_MODE=real`/`local_real`, `LLM_CLIENT_MODE=claude`), confirm the backend actually
   boots and serves in that config before handover.

## Confirmed understanding: §13 vs §13B are DISTINCT layers

- **Section 13 = the STATE MACHINE / real stateful loop.** It makes the recommendation lifecycle
  genuinely stateful: statuses actually transition and persist, completing one generates a real
  persisted consequence (impact-ledger transaction linked by edge), the change is really visible on
  other screens, the AI Assistant really reflects it, recommendations really regenerate. It is about
  the *system's behavior* being real end-to-end.
- **Section 13B = the GUIDED-NARRATIVE layer built ON TOP of that real loop.** It does not add new
  state or fake anything — it makes the already-real flow *legible*: a left-to-right pipeline-trace
  view of any AI output's real journey, a scripted replayable guided scenario that drives the real
  app through the real §13 loop step by step, a rollup-persona journey, and an ROI summary from the
  real recorded outcomes. It is about the real behavior being *followable as a story*.

In one line: **§13 makes the loop real; §13B makes the real loop watchable.** 13B depends on 13 and
must not be started until 13's loop is genuinely working with real evidence.

## Standing rules for this run
- Commit after every numbered sub-item; push at every section boundary minimum.
- Update PROGRESS.md continuously.
- Every "done" claim needs REAL evidence (before/after values, screenshots, command output) — never
  a status assertion alone.
- Every AI-behavior check uses REAL Claude (`LLM_CLIENT_MODE=claude`), never mock.
- Diagnose root cause before fixing; state for each item whether it's a §11 regression, an
  original never-closed gap, or a clarification.
- Screenshots → `docs/qa_screenshots/` (persistent, gitignored), never /tmp.
- Do not stop for routine check-ins — only a genuine blocker (document, move on) or approaching
  usage limit (finish + commit current item cleanly).

## User clarification (mid-run) — NEW SURFACES for parts of 13/13B
Fold in when reaching §13/§13B. Some items need genuinely NEW screens (nav entry, real data,
design-system consistent) — do NOT cram into an existing page:
- **13B.2 guided-scenario walkthrough** → a guided overlay/mode layer over the real app (new surface).
- **13B.4 business-impact/ROI summary** → its own dedicated view (new page).
- **13.2 impact ledger** → a visible view of recommendation→consequence records (new page), not just stored data.
Everything else in 12/13/13B stays an extension of an existing page (pipeline-trace extends
Explainability, state-machine UI extends Opportunities, etc.). Rule: new surface when cramming would
compromise either page; extension when it genuinely belongs with existing content.

## ALL SECTIONS ADDRESSED ✅ — §12 → §13 → §13B → §10 → §14 (master order complete)
Final state (all pushed):
- **§12** Regression fixes — 10/10 done (dashboard, filters/charts, real US map, centrality, funnel, advisor
  selectors, feature-lab re-verify, visible feedback, admin, Chase Wealth Management rename).
- **§13** Stateful lifecycle — state machine + impact ledger + exact +impact propagation on 3 screens +
  AI-awareness + regeneration + Impact Ledger page. verify_section13_lifecycle.py ALL PASSED.
- **§13B** Story mode — pipeline-trace bar, Guided Story Mode overlay (live proof "+$52,111 = exactly the
  impact"), Business Impact & ROI page. verify_section13B_story.py ALL PASSED. (13B.3 division journey deferred.)
- **§10** Real header search + notifications done; rest satisfied by §11-13B or deferred (AUM waterfall,
  PDF/PPT export, household/AGP model extensions) — all additive, no new architecture.
- **§14** real+claude handover config verified boots+serves; **real Claude works** (key is in the OS env, not
  the .env file — earlier "blocked" notes corrected). Running config = GRAPH_CLIENT_MODE=real, LLM_CLIENT_MODE=claude.

Deferred (next session, all additive): §13B.3 division story · AUM net-flows waterfall · PDF/PPT export ·
household next-best-product/concentration/review-cadence · strengthen the AI-Assistant explicit
completion-narration (prompt weighting for the RECOMMENDATION_LIFECYCLE context item).

---

## §12 ✅ · §13 ✅ · §13B ✅ (all pushed) — §10 (remaining) → §14 detail below
- §13B: pipeline-trace bar (Explainability), Guided Story Mode overlay (/story, verified live: proof chip
  "+$52,111 = exactly the impact"), Business Impact & ROI page (/business-impact). 13B.3 division journey
  deferred (additive follow-up, engine supports it). verify_section13B_story.py ALL PASSED.
- Remaining: §10 (re-check each vs what §11-13B built; do only genuinely-unbuilt bounded items) → §14
  (flip to real graph + real LLM for handover; blocked on client's ANTHROPIC_API_KEY + TigerGraph — document).
- §13: full stateful lifecycle verified (state machine, impact ledger, exact +impact propagation on 3
  screens, AI-awareness plumbing, regeneration exclusion, new Impact Ledger page). 13.8 trace ALL PASSED.
  Only the real-Claude 13.4 answer-text check is blocked on the missing ANTHROPIC_API_KEY (documented).

## Progress — Section 12
- [x] 12.1 Executive Dashboard — DONE. New `/scope/dashboard` + `/scope/ai-insight` (period + Compare-To
  aware). Added Revenue Trend, Revenue by Product Category (donut), Revenue Drivers vs Prior Year (YoY bars),
  Benchmarking vs Peers (per-advisor bars + firm-avg line + percentile), Top & Bottom Markets, AI Insight
  Summary (grounded), AI Coaching (Advisor scope only), explicit Bottom Advisors + AUM/Why detail. Removed
  Business Outcomes strip. Added Reset-filters. VERIFIED real re-roll: Firm/YTD $22.2M/−0.8% → Eastern
  Division/QTD $1.3M/+19%, 0 console errors (s12-1-dashboard-firm.png, s12-1-dashboard-division-qtd.png).
