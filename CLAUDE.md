# iPerform Insights & Coaching — Rebuild Brief (for Claude Code)

This file is the source of truth for this build. Read it fully before writing code.
Update `PROGRESS.md` at the end of every session (see convention at the bottom).

## 0. Context

This is a rebuild of an existing partially-built repo (`iperform-insights-coaching/`).
Full specification lives in:
- `docs/spec/iPerform_Insights_Coaching_Complete_Rebuild_Specification_v1_1.md` (authoritative, 1524 lines)
- `docs/spec/iPerform_Insights_Coaching_Data_Mapping_and_Query_Workbook_v1_1.xlsx` (27 sheets: schema deltas, GSQL catalog, API catalog, page blueprints, etc.)
- `docs/spec/mockups/*.png` (UI reference)

Client priority: **the demo must clearly show the agentic AI pipeline working end-to-end** —
Feature Engineering → Embeddings/Similarity → Predictions → Opportunities → Recommendations →
Feedback/Outcome → Learning signal (RL-style reward/rank update) — running on real, internally
consistent business data (hierarchy, revenue, AGP, CRM). This pipeline is the priority; breadth
across all 32 pages/9 personas is secondary and comes after the pipeline works end-to-end for
one persona (Advisor) and one scope path.

**Network constraint:** the machine running this build has normal internet access (PyPI, npm)
but CANNOT reach the client's TigerGraph or Azure OpenAI endpoints — those are only reachable
from the client's environment. Do not treat this as a reason to fake business logic. See
Section 2 (Adapter Pattern) — it is a hard requirement, not a shortcut.

## 0B. MANDATORY FIRST STEP: Route Reality Audit (before touching Streamlit or any page)

Investigation during planning found the React frontend already has TWO parallel, disconnected
implementations for several capabilities — this is worse than simply missing functionality, and
must be resolved deliberately, not by guessing which one to keep.

Confirmed findings to start from:
- Real backend logic exists for feature store (`app/services/feature_store_service.py`, exposed
  at `/features/*`) AND a second, separate, also-real implementation
  (`app/features/*` — `FeatureRuntime`, `PredictionRuntime`, `SimilarityService`, exposed at
  `/feature-runtime/*`). These are redundant, not complementary — consolidate to one.
- Real backend logic exists for agentic reasoning (`app/services/agentic_ai_service.py`, exposed
  at `/agentic-ai/run`, returning answer/confidence/tasks/evidence/reasoning_steps) and for
  orchestration (`app/orchestration`, exposed at `/orchestration/run`).
- The frontend has a set of properly-wired components (`frontend/components/feature-runtime/`,
  `orchestration/`, and others alongside them — `graph-runtime`, `knowledge-runtime`,
  `memory-runtime`, `recommendation-runtime`, `llm-activation`, `tigergraph-activation`) that call
  real endpoints — but per `frontend/lib/navigation.ts`, these are **NOT in the visible sidebar
  navigation** (only 16 items are linked; check the current list before assuming it's still
  accurate). A user cannot reach them through the app.
- What IS in the visible navigation for "Feature Store / Embeddings / Similarity" and "Memory
  Timeline & Explainability" are the fake, hardcoded `frontend/components/remediation/dense-ui.tsx`
  pages calling `/ui-remediation/*` (see Non-Negotiables above for why these must not survive).
- The Streamlit agentic reasoning console (confidence/evidence/reasoning-steps detail) has **no
  reachable equivalent at all** in the current navigation, real or fake.

**Required steps, in order, before any other work begins:**
1. Enumerate every backend service/module that implements business logic (feature engineering,
   prediction, similarity, recommendations, agentic reasoning, orchestration, memory, knowledge).
   For each, list every router that exposes it and flag duplicates like the feature store case
   above.
2. For each duplicate pair, pick the more complete/correct implementation and mark the other for
   deletion — record the decision and reasoning in `PROGRESS.md`. Do not keep both "just in case."
3. Enumerate every route in `frontend/lib/navigation.ts` (or wherever it currently lives) plus
   every `page.tsx` under `frontend/app/(dashboard)/`, including ones with no nav entry. For each,
   identify which component it renders and which API(s) that component calls.
4. Classify each page: (a) real component + real API + in nav → keep, restyle to Section 1B
   design system; (b) real component + real API + NOT in nav → add to nav, restyle, verify it
   actually works end to end; (c) fake `dense-ui`/`remediation` page currently in nav with a real
   counterpart existing elsewhere → replace with the real one, don't rebuild from scratch; (d) fake
   page with NO real counterpart anywhere → build it for real against the consolidated backend
   from step 2; (e) capability with no frontend at all (e.g. the agentic reasoning/evidence/
   confidence console) → build a real page for it, using the shared design system, exposing
   reasoning_steps/evidence/confidence with the same depth the Streamlit console had.
5. Only after this classification is complete and recorded in `PROGRESS.md`: delete
   `frontend/components/remediation/dense-ui.tsx` and every `/ui-remediation/*` backend route,
   and proceed with Streamlit removal (Phase 1) as originally planned. Streamlit itself is safe to
   delete — nothing found lives ONLY in the Streamlit pages with no equivalent backend service —
   but do not delete it before this audit confirms that for every page, not just the ones spot-
   checked during planning.

## 1. Non-Negotiables (from spec Section 5, FOUND-001..005)

- No Streamlit anywhere. Delete `app/ui/` entirely and remove `streamlit` from `pyproject.toml`.
- Frontend: React/TypeScript (Next.js, already scaffolded in `frontend/`) — reuse the scaffold,
  routing, and design tokens, but replace the generic `dense-ui.tsx` template approach.
- Every page must be a real, distinct component matching its entry in the Page Blueprints sheet —
  not a shared generic template with different props.
- Every "AI" output (prediction, recommendation, insight, similarity score) must persist a
  traceable artifact (which features/evidence produced it) — not just return a number.
- Backend business logic (feature engineering, prediction scoring, recommendation ranking,
  opportunity detection, learning/feedback updates) must be real code, not hardcoded response
  dictionaries. This is the #1 defect found in the audit of the existing repo — do not repeat it.

## 1B. Design System & UI Construction (read before writing a single component)

The prior build's core UI defect: every page routed through one generic hardcoded template
(`PageFrame`/`Section`/`StatusRow`, ad hoc inline hex colors, "Graph: MOCK" literally in the
header). Do not repeat this. The reference mockups already pin a specific, considered visual
direction — the job is disciplined extraction and reuse, not fresh creative invention.

**Reference stack** (confirmed by the client's own approved mockup footer: "Next.js 14 ·
TypeScript · Tailwind CSS · ShadCN UI · Recharts · Framer Motion") — use this exact stack, not
MUI, even though an earlier spec draft mentions MUI. The mockups are the more specific and more
recent source of truth.

**Step 0 — Build the token system first, as its own reviewable unit, before any page:**
- `frontend/styles/tokens.ts` (or Tailwind theme config extension) with named values, not
  scattered inline hex:
  - Primary blue ~`#2563EB`, teal/positive ~`#14B8A6`, violet/AI-accent ~`#7C3AED`,
    amber/warning ~`#F59E0B`, red/negative ~`#DC2626`, slate neutrals for text/borders/surfaces.
  - Two theme surfaces exist in the references — a dark navy sidebar (`#0B1220`–`#0F172A`) with
    a light content canvas (`#F8FAFC`), and a fully light variant. Pick ONE as the system default
    (dark sidebar + light canvas, matching the majority of references) and use it consistently;
    don't mix both across pages.
  - Severity palette must map 1:1 to the spec's Severity_Model sheet (on-track/attention/urgent/
    critical or good/warn/bad) and be reused everywhere status is shown — never redefined
    per-component like the old `cls()` helper duplicated inline logic.
  - Type scale: dense enterprise data-table sizing, not marketing-site sizing — labels at
    11-12px uppercase tracked, body/data at 12-13px, KPI values bold at 20-24px, page titles
    ~20px bold. Confirm against the mockups' visual density before building — these screens are
    information-dense by design, not spacious.
  - Spacing/radius/elevation scale: rounded-xl/2xl cards, subtle border + soft shadow, consistent
    gap scale (not ad hoc `gap-2`/`gap-3`/`gap-4` chosen per component).
- Build the shadcn/ui primitives needed (Card, Badge, Button, Select, Tabs, Table, Sheet/Drawer,
  Dialog, Skeleton) configured against these tokens ONCE, in `frontend/components/ui/`.
- Build the recurring composite patterns ONCE and reuse them everywhere they recur across pages:
  KPI stat card (icon + label + value + delta badge), AI-generated content card (with the
  "AI Generated" chip treatment seen in the references), agent/evidence trace pill row, severity
  status row, chart card wrapper. These map to the workbook's Component_Catalog sheet — build
  against that sheet's inventory, don't invent ad hoc equivalents.

**Step 1 — Self-check before moving on:** does this token set and component set look like it was
chosen for a wealth-management enterprise analytics product, or could it be dropped into any
generic SaaS dashboard unchanged? If the latter, it hasn't actually captured the reference
material yet — revise before building pages on top of it.

**Per-page construction rule:** every page in the Page Blueprints sheet gets its own component
built from the shared primitives above, matching that page's specific mockup/blueprint layout —
never routed through one shared generic frame. Charts use Recharts with the shared color tokens,
not per-chart hardcoded color arrays. Motion (Framer Motion) is restrained and purposeful — page
transitions, subtle hover/press states, loading skeletons that match final layout shape — not
decorative animation.

**Visualization-type rule (mandatory):** every page must render data using the SAME
visualization type the reference mockup uses for that concept — a plain number or table is not an
acceptable substitute when the mockup shows a chart. Map concept → form:
- trend / change over time → **line chart** (e.g. monthly revenue/AUM, recommendation impact
  over the feedback sequence);
- part-of-whole / category breakdown → **donut/pie** (e.g. book composition by account type),
  but only when the categories actually vary — a single-category donut is not a chart, use the
  table/number instead;
- comparison across items → **bar chart** (e.g. product-mix revenue, peer benchmark);
- embedding / feature-vector space → **2D projection scatter** via real dimensionality
  reduction (PCA or similar) over the real vectors — never fabricated coordinates;
- entity relationships → **network/graph diagram**.
Use table/list ONLY where the mockup itself uses a table/list (households table, recommendation
queue, evidence list) — and conversely, do NOT chart things that were never charts. Recharts is
the chart library; every chart reads real API data and the shared color tokens (validate any
multi-series categorical palette against the dataviz skill's checker), never decorative sample
data. This applies to Phase-11 pages too (Exec/DDW/RDW command centers, Revenue Intelligence,
Book of Business) — they are the most chart-dense screens in the set.

**Quality gate:** after Step 0, and again after the first 2-3 pages are built, take a screenshot
of the running app and compare side-by-side against the corresponding reference mockup before
continuing to the next page. Note and fix any drift (density, color, type weight) immediately —
don't defer visual QA to the end, since by then it compounds across all 32 pages.

## 2. Adapter Pattern (required architecture)

Define two interfaces in `app/graph/client.py` and `app/llm/client.py`:

```python
class GraphClient(Protocol):
    def run_query(self, query_name: str, params: dict) -> dict: ...
    # one method per GQ-### query in the GSQL_Queries catalog sheet, or a generic dispatcher

class LLMClient(Protocol):
    def generate(self, prompt: str, context: dict) -> str: ...
```

Implementations:
- `RealGraphClient` — pyTigerGraph, reads host/user/pass/graph from env. Implements every
  GQ-### query from the workbook as real GSQL, installed via `tigergraph/queries_v1` and
  `tigergraph/queries_v2`. This code should be correct and complete even though it can't be
  executed here — write it carefully against the documented schema.
- `MockGraphClient` — same method signatures, same return shapes as the real client, but reads
  from a locally seeded dataset (see Section 3). This is what actually runs during this build.
- `RealLLMClient` — Azure OpenAI SDK, env-configured endpoint/deployment/key. This is what runs
  at the client site.
- `ClaudeLLMClient` — Anthropic SDK (`pip install anthropic`), reads `ANTHROPIC_API_KEY` from
  env. **Default model: `claude-haiku-4-5-20251001`** — cheapest tier, sufficient quality for
  demo insight/coaching/chat text. Do not default to a more expensive model without being asked.
  This is what runs locally during this build to validate real, coherent LLM output instead of
  templated mock text — same purpose as the local TigerGraph setup, but for the LLM side. Uses
  the exact same prompts/inputs the real Azure OpenAI implementation will use, so nothing about
  prompt design changes at cutover — only the env config.
- `MockLLMClient` — deterministic template-based generator using the same prompt inputs. This
  stays the default driver for routine iteration (free, instant); switch to `ClaudeLLMClient` only
  when spot-checking output quality, not on every reload — no need to burn real tokens on every
  hot-reload cycle.

**Security:** `ANTHROPIC_API_KEY` goes in `.env` only, never in any committed file, never in
`PROGRESS.md`, never pasted into a Claude Code session transcript intentionally. Confirm `.env`
is in `.gitignore` before the first commit that could contain it.

Selection via `.env`: `GRAPH_CLIENT_MODE=mock|local_real|real`, `LLM_CLIENT_MODE=mock|claude|real`.
Default to `GRAPH_CLIENT_MODE=mock` and `LLM_CLIENT_MODE=mock` in `.env.example` for anyone
cloning this without credentials; this repo's actual working `.env` (gitignored) can run
`LLM_CLIENT_MODE=claude` once the API key is added. All service/business logic code must depend
only on the `GraphClient`/`LLMClient` interfaces — never import `pyTigerGraph`, `openai`, or
`anthropic` outside their respective `Real*`/`Claude*` implementations.

If a local TigerGraph Developer Edition (Docker) becomes available, add a third mode
`GRAPH_CLIENT_MODE=local_real` using `RealGraphClient` pointed at localhost — this validates real
GSQL syntax/schema without needing the client's instance. Optional, not required to proceed.

## 3. Seed Data — SUPERSEDED, use the verified TigerGraph Foundation package

A separate package (`iperform_story1_tigergraph_foundation_v0.2.0`, delivered as
`docs/tigergraph_foundation/` in this repo) already provides a verified, independently-checked
graph foundation. Do not regenerate seed data or GSQL from scratch — use this package as the
source of truth for Phases 2-3 below:

- `tigergraph/schema/` — 56 vertices, 126 directed edges + 126 reverse edges. Verified: every
  edge FROM/TO type resolves against a declared vertex, zero dangling references.
- `tigergraph/loading/jobs/` — 182 server-side GSQL loading jobs, one per manifest entry, column
  order verified against schema attribute order.
- `tigergraph/queries/` — all 43 GQ-### queries from the workbook's GSQL_Queries catalog,
  verified: every edge/vertex reference in every query resolves against the schema (0 errors
  across an automated structural check of all 43 files).
- `data/manifest.json` + `data/sample/` — 182 CSV files, 109,328 rows, verified to exactly match
  manifest expected row counts and column mappings (0 discrepancies).
- `backend/app/services/tigergraph_client.py`, `ingestion_service.py`, `manifest_service.py`,
  `graph_validation_service.py` — real, reusable RESTPP ingestion logic (proper TigerGraph
  upsert payload construction, mock/live mode toggle, batch/checkpoint/retry handling). Port
  these into `app/graph/` as the implementation backing for `RealGraphClient` and the CSV-based
  seed loader for `MockGraphClient` — do not rewrite this logic from scratch.

**Reconciliation status: RESOLVED.** Confirmed with the user — the client's live TigerGraph
instance has no existing data. The old 42-vertex/81-edge graph does not need to be preserved or
migrated. This package's 56-vertex/126-edge schema is approved as the new baseline outright: the
existing graph (if any objects exist) can be dropped and recreated from this schema with no
migration step. Do not re-raise this as an open question.

Use this package's own `make validate` / `scripts/validate_*.py` as the ongoing correctness gate
for any further schema/query changes — don't hand-edit GSQL without re-running them.

## 3B. Consolidate the ingestion console as a page in the main app

The foundation package ships its own small React/MUI "Data Management console" (upload, sync
status, validation) as a separate app. Don't keep it as a second standalone frontend — that
recreates the two-frontends problem from Section 1. Instead:

- Port `backend/app/routers/{catalog,graph,ingestion}.py` and their backing services into the
  main FastAPI app as an `app/ingestion/` module (the logic is sound, reuse it as-is where
  possible). Note: the base repo already has a non-empty `app/ingestion/` (~575 lines) from the
  original build — compare both before merging, keep whichever is more complete per function, do
  not just overwrite one with the other silently. Record which parts came from which source in
  `PROGRESS.md`.
- Rebuild only the UI shell as a page in the main Next.js app — this maps directly to the spec's
  `DATA` (Data Health) and/or ingestion-related page blueprint — using the shared design system
  and primitives from Section 1B, not MUI. Functionality (upload, manifest-driven sync,
  batch/checkpoint status, error/hash reporting) carries over; only the visual layer is rebuilt
  to match the rest of the app instead of living in a visually separate MUI tool.

## 4. Seed Data (original scope, now reduced to gap-filling only)

The above package covers the full business/AGP/CRM/AI data model already. Only build additional
generator logic here for anything it doesn't cover once you've reviewed it against the Feature/
Memory/Prediction/Severity catalog sheets — check before assuming a gap exists.

## 5. Build Order

1. **Foundation**: Remove Streamlit. Stand up adapter interfaces + mock implementations (empty
   data OK initially).
2. **Local TigerGraph via Docker — do this now, not last** (see Section 8 for exact steps). The
   schema/queries package (Section 3) is already finalized and verified structurally; the sooner
   it's confirmed to actually compile and load on a real engine, the cheaper any fix is. If this
   succeeds, switch to `GRAPH_CLIENT_MODE=local_real` as the default working mode for the rest of
   the build — develop against real query results, not assumed mock shapes. If Docker setup
   fails or the machine can't handle it after one focused attempt, fall back to
   `GRAPH_CLIENT_MODE=mock` and proceed — don't let this block the rest of the build either way.
3. **Data access layer**: Implement every "Required" GQ-### query call site against whichever
   `GraphClient` is active (real-local or mock).
4. **AGP + CRM backend modules**: `app/agp/` and `app/crm/` are currently empty — build real
   domain logic here (milestone/KPI calculation, on/off-track logic per AGP-004, lead/referral/
   opportunity tracking per CRM-001..005).
5. **Feature Engineering**: `app/features/` — compute real feature snapshots from seed data per
   the Feature_Catalog sheet, with lineage (which raw facts produced which feature value).
6. **Embeddings + Similarity**: `app/embeddings/` — real vector generation (can be a lightweight
   deterministic embedding, doesn't need a real model) + nearest-neighbor search, persisted.
7. **Predictions**: `app/prediction/` — real scikit-learn models (or deterministic scoring
   functions if training data is thin) producing scores + feature contributions + confidence,
   per Prediction_Types sheet.
8. **Opportunities + Recommendations**: `app/opportunities/`, `app/recommendations/` — real
   detection/ranking logic consuming predictions + features, with severity/impact per
   Severity_Model sheet, distinct from CRM opportunities (per CRM-003).
9. **Feedback + Learning loop**: `app/feedback/` — accept/reject/complete actions update a
   learning signal that visibly affects future recommendation ranking/confidence. This closing
   loop is the centerpiece of the demo — it must be visibly wired, not decorative.
10. **Frontend wiring — pipeline pages first**: Advisor 360, Feature Engineering Lab, Embedding &
    Similarity Lab, Predictions Center, Recommendations, Explainability Explorer, AI Assistant,
    Feedback & Learning — each showing real data from the API, not hardcoded. Persona/role
    selection + hierarchy-aware navigation per spec Section 3.
11. **Breadth**: remaining command-center pages (Exec/DDW/RDW/MDW), Revenue Intelligence,
    Hierarchy Explorer, Book of Business, remaining AGP/CRM pages, Graph Explorer, Knowledge
    Search, Admin/Observability — reusing the now-proven patterns from step 10.

Skip: automated test suites (explicitly deprioritized this round). Manual verification against
running mock stack is sufficient for now.

## 6. Definition of Done per phase

A phase is done when: the relevant API endpoint(s) return data sourced from the seed dataset
through real business logic (not a hardcoded dict), the corresponding frontend page renders that
data with no console errors, and the artifact chain (feature → prediction → opportunity →
recommendation → explanation → feedback) is traceable end-to-end for at least one advisor.

## 7. Progress Log Convention

Maintain `PROGRESS.md` at repo root. At the end of every work session, append:

```
## Session N — <date/time>
Completed: <what actually works now, verified how>
In progress: <what's partially done>
Known issues / deferred: <e.g. real GSQL untested against live TigerGraph>
Next: <the next 1-3 concrete tasks>
```

At the start of every session: read `PROGRESS.md` and `git log` before doing anything else, then
continue from "Next" rather than re-deriving priorities.

## 8. Local TigerGraph via Docker (do this early — see Section 5, step 2)

Attempt this right after Foundation, time-boxed to one focused session. If it works, it becomes
the default `GraphClient` backing for the rest of the build (`GRAPH_CLIENT_MODE=local_real`). If
it doesn't — hardware constraints, Docker issues — fall back to `GRAPH_CLIENT_MODE=mock` and
don't let it block Phase 3 onward; the adapter pattern means nothing downstream cares which mode
is active.

Use the **Community Edition** image, not Enterprise — it requires no license key at all (free
even for production use, up to 300GB / 16 CPUs, single-server only, GSQL + OpenCypher). This
avoids the Enterprise free-license request flow entirely, which is unreliable to depend on since
TigerGraph's signup page has changed layout/flow multiple times. Single-server/no-clustering and
no professional support are the only real limitations, neither of which matters here.

Prerequisite (human must do this, not automatable): Docker Desktop installed, with resources
allocated (TigerGraph recommends 8 cores / 24GB RAM, or ~80% of available; if the laptop is
lighter than that, expect it to be slow or to fail — abandon and fall back to mock if so).

Steps:
```bash
docker pull tigergraph/community:latest
docker run -d --init -p 14022:22 -p 9000:9000 -p 14240:14240 --name tigergraph \
  --ulimit nofile=1000000:1000000 -v ~/tigergraph-data:/home/tigergraph/mydata \
  -t tigergraph/community:latest
# wait 1-2 minutes for services to initialize, then verify:
docker exec -it tigergraph gadmin status
```
No license activation step needed — it's ready to use as soon as `gadmin status` shows all
services up. Verify GraphStudio is reachable at `http://localhost:14240`. Then install the
verified schema, loading jobs, and queries from the TigerGraph Foundation package (Section 3):
`tigergraph/schema/*.gsql`, `tigergraph/loading/jobs/*.gsql`, `tigergraph/queries/GQ-*.gsql`, load
the 182 CSVs from `data/sample/` per `data/manifest.json`, and add a `GRAPH_CLIENT_MODE=local_real`
option pointing `RealGraphClient` at `localhost:9000`/`localhost:14240`. Since this schema/data
was already verified structurally (Section 3), this step mainly confirms it also compiles and
loads on an actual TigerGraph engine — the one thing static analysis can't fully prove.

If `tigergraph/community:latest` has issues, try a pinned version tag such as
`tigergraph/community:4.2.2` instead of `latest`.

Note: this validates GraphClient/GSQL only. LLMClient stays mocked regardless — there is no
equivalent free local stand-in for the client's Azure OpenAI deployment worth setting up here.
