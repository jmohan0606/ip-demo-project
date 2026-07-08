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

**Quality gate:** after Step 0, and again after the first 2-3 pages are built, take a screenshot
of the running app and compare side-by-side against the corresponding reference mockup before
continuing to the next page. Note and fix any drift (density, color, type weight) immediately —
don't defer visual QA to the end, since by then it compounds across all 32 pages.

**Screenshot location — standing rule, no exceptions:** always save screenshots to a project-
relative, persistent path (`docs/qa_screenshots/`, gitignored) — never `/tmp` or any scratchpad
path outside the repo. Ephemeral storage is wiped on every codespace restart; this has already
caused a lost-workspace confusion once in this project. This applies to every screenshot taken
anywhere in this project, not just during Section 1B's own construction.

**Visualization fidelity rule (added after Phase 10 review — real gap found, not optional
polish):** every page must render data using the visualization type the reference mockups use
for that concept — line chart for trends over time, donut for category breakdown, bar for
comparisons, scatter/projection for embeddings/similarity, network diagram for relationships,
radar for multi-metric peer comparison, funnel for pipeline stages, map for regional data.
Recharts is available — use it. Do not render a plain number/table where the mockup shows a
chart; conversely, don't invent a chart for something the mockup itself renders as a table/list
(households table, recommendations list). Every chart must be backed by real computed data with
the underlying query/computation stated as evidence — charts are not exempt from this project's
evidence bar.

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

## 5B. Phase 11 expanded scope (added after Phase 10 review — do this before/during breadth pages)

Review of the first 7 built pages against the reference mockups found gaps beyond visual
polish. Before or during Phase 11, address all of the following:

**1. Mockup-to-build page audit (do this first, produce a report before building more pages).**
View every file in `docs/spec/mockups/` directly (don't rely on a prior text description of
them) and enumerate every distinct page/screen shown across all of them, including which nav
group/persona each belongs to. Cross-reference against `frontend/lib/navigation.ts` (or wherever
the current nav list lives) and the actual built pages. Produce a table: mockup page → exists in
nav (Y/N) → has real content built (Y/N) → notes. Known gaps to confirm and fill:
- **What-If Scenario Simulator** — in nav (labeled "New") but not built. Must run on real
  advisor data: take a real advisor's current feature snapshot, apply a user-adjustable
  parameter (e.g. "increase meetings by 20%"), and show a real projected impact — either by
  re-running the actual feature→prediction→opportunity chain with the adjusted input, or a
  clearly-labeled deterministic projection formula using real current values as the baseline.
  Do not fabricate projected numbers unrelated to the advisor's real data.
- **Executive/DDW/RDW/MDW command-center pages** — these are leadership/rollup views (see the
  "iPerform Insights" mockup showing persona "DDW" with Executive Overview, Advisor Performance,
  AGP Program Dashboard, Peer Benchmarking at a division/region level) — aggregate real per-
  advisor data up to the selected hierarchy scope, don't hardcode firm-wide numbers.
- Any other mockup page not yet in the nav or not yet built — add to the audit report and build
  during Phase 11.

**2. Fix the top filter bar** (visible defect, not just style): remove the duplicate "Advisor" /
"Advisor" dropdown pair, implement a real hierarchy breadcrumb (Firm > Division > Region >
Market > Advisor, per spec Section 3's persona/hierarchy model) that actually scopes page data
when changed, and add a properly-styled system-status indicator matching the mockups (not the
current ambiguous "Ready" pill). Apply this fixed filter bar consistently across all pages.

**3. Persona/role scoping — decision made, implement as scope-aware data, not access control.**
The mockups show persona-specific dashboards (Advisor view vs. DDW/division-leadership view).
Full role-based access control (login, permissions, page-gating per role) is more than this demo
needs and risks becoming its own project. Instead: implement persona/hierarchy selection as a
**data-scoping control** — the same underlying pages adapt what data they show based on the
selected persona + hierarchy level (e.g. Executive Dashboard shows firm-wide rollups when
scope=Firm, division rollups when scope=Division, one advisor's data when scope=Advisor), using
the hierarchy breadcrumb from item 2 as the actual control. Do not build separate login/auth or
page-visibility gating per role — that's out of scope. If this interpretation doesn't fit
something specific found during the mockup audit, flag it rather than guessing further.

**4. Continue applying the visualization fidelity rule (Section 1B)** to every Phase 11 page —
these are the most chart-heavy pages in the mockup set (donuts, bar-by-channel, region maps,
radar peer-benchmarks, funnels). Don't let breadth pages regress to numbers-and-tables.

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

## 9. Client Review Round 2 (2026-07-05) — enterprise UX, missing components, new infra

Comprehensive client review after Phase 11 closure. Root theme: the pipeline/data layer has
been repeatedly proven real and correct (see PROGRESS.md/VERIFICATION_CHECKPOINT.md) — this
round's issues are almost entirely (a) pages not consuming the real scope/hierarchy context that
already exists, (b) UI components that are plainer than enterprise wealth-management standards
require, and (c) real feature/infra gaps (MCP adapter tier, richer data, new capabilities). Work
this section in the priority order below — each tier fixes/unblocks the one after it.

### 9.0 Non-negotiable design correction: NO PURPLE anywhere

Client-directed change, overrides the original Section 1B token choice. Replace the violet
`#7C3AED` "AI Generated" accent with a professional, non-purple alternative (e.g. a deep
teal/indigo-blue distinct from the existing severity blue) — pick one and apply it consistently
everywhere the AI-generated chip/accent appears. Audit every page for any remaining purple/violet
and replace.

### 9.1 PRIORITY 1 — Root-cause: advisor-scope-following (fixes 5 pages at once)

Predictions, Opportunities & Recommendations, AI Assistant, Feature Engineering Lab, and
Explainability Explorer are hardcoded to advisor A001 and do not respond to the hierarchy
breadcrumb / advisor selector built in Phase 11 Part 2/4. This is a frontend wiring gap, not a
backend gap — the backend has been proven repeatedly to return different, correct data per
advisor. Fix: make all 5 pages consume the shell's scope context (same pattern already used by
advisor-360, dashboard, revenue-analytics, etc. since Part 4) and re-fetch when the selected
advisor changes. Verify with real screenshots: same page, two different advisors selected,
visibly different data.

### 9.2 PRIORITY 2 — Filter bar fixes (affects every page)

- Filter/scope selection must be persistent and navigable — going to a different page and back
  must not lose the selected scope. Fix the underlying state management (shell-level context is
  correct; audit for any page-level override that resets it).
- The Time Period dropdown does nothing — wire it to actually filter/re-scope displayed data.
- Add a "Compare To" selector (compare current period to a selectable prior period), matching
  the Hackathon mockup's filter bar.
- Clarify or fix the refresh/search/alert icon buttons at top — each must either do something
  real (refresh = re-fetch current page data; search = real search; alert = real
  notifications/system alerts) or be removed. No decorative dead buttons.

### 9.3 PRIORITY 3 — Data model & sample data expansion

- **Real-world entity names**: divisions, regions, markets, branches, households, accounts,
  portfolios, opportunities, leads, referrals currently use generic placeholder names
  ("Household 1", "Division 1"). Replace with plausible real-world names throughout the seed
  data generator (e.g. real-sounding firm/branch/household names) — this affects perceived
  quality on every page.
- **Richer, wider sample data**: current date range is too narrow for meaningful trend/seasonal
  visuals (e.g. the new Revenue Trend feature in 9.6 needs multi-year monthly granularity).
  Expand the seed generator's time range and volume where current data can't support new
  visualizations (geographic map needs real region/market distribution; top/bottom
  markets/branches needs enough branches to rank; CRM needs realistic lead/referral/opportunity
  variety, not near-duplicate rows).
- **Schema changes**: if a requirement below needs a vertex/edge/attribute that doesn't exist
  (e.g. branch performance, coaching task assignments, saved what-if scenarios), add it to the
  TigerGraph schema (`tigergraph/schema/`) and update the manifest/loading jobs/mock seed data
  consistently — same rigor as the original foundation package validation (structural checks
  before assuming it works).
- Do this before/alongside 9.4-9.7, since several of those page rebuilds depend on data that
  doesn't exist yet in adequate form.

### 9.4 PRIORITY 4 — TigerGraph adapter: 4-tier fallback chain (client standard)

Extend the Section-2 `GraphClient` adapter with a proper tiered fallback, using the client's
actual standard stack:
- **Tier 1 — `tigergraph-mcp`** (official package, github.com/tigergraph/tigergraph-mcp / PyPI
  `tigergraph-mcp`, built on pyTigerGraph's async APIs) for AI/agent-driven graph access and
  query execution. This is the primary path for anything agent-initiated.
- **Tier 2 — `pyTigerGraph`** direct (sync/async connection) as fallback if the MCP server is
  unavailable, and as the standard path for non-agent backend code (the client's other standard).
- **Tier 3 — RESTPP** direct (the current `RealGraphClient`) as fallback if pyTigerGraph itself
  can't connect.
- **Tier 4 — `MockGraphClient`** (current default) as final fallback.
Implement as one adapter with automatic tier fallback on connection failure, logging which tier
actually served each request (for the Admin/Data Health page's adapter-status display). This is
new architecture — Fable-appropriate (see Section 9.9 model routing).

### 9.5 PRIORITY 5 — Page-by-page rebuilds (condensed from full client feedback; treat each as a
real requirement, not a suggestion — build the backend logic behind each if it doesn't exist yet)

**Executive Dashboard**: Add — AI Insight Summary card (Key Drivers / Watch Outs / What to
Monitor structure, matching the Hackathon mockup exactly); AI Coaching Card (Recommendation /
Shoutout / Action Steps / Guideline Basis); Revenue by Product Category AND Sub-Category;
Revenue Drivers vs prior year; Peer Benchmarking; Recent Transaction Highlights; Top/Bottom
Markets; consider Branch Performance. Every KPI card needs a small icon + up/down arrow +
%/point delta vs prior year, green/red color-coded. Donut charts show the total value centered
inside the donut. Top AND bottom advisors, each with a stated reason why. AGP Program Status
card (on-track/off-track counts + link to AGP page). "View Details" link on every card whose
full detail lives elsewhere (link to the real page, or a modal if no dedicated page exists yet
— build the modal's content for real, don't stub it).

**Revenue Analytics**: Add a real geographic map (revenue by region/market/location, not a
placeholder). Build out beyond one line + one donut to match enterprise BI standards (channel
bar, cohort/product breakdowns, etc., per the mockups already provided). Fix "Revenue by scope"
— currently broken, diagnose and repair.

**Advisor 360 / Client 360**: AGP status card must only render for advisors actually enrolled in
AGP — hide/adapt for non-AGP advisors, page must serve both populations well. Add AI Insight
Summary + AI Coaching Card (same structured format as the dashboard, per-advisor). CRM execution
cards color-coded by outcome (won=green, lost=red, negotiate=amber). Clarify or remove "AI
artifacts" section — make it meaningful (link to real explainability/lineage) or drop it.
Households table: add a visual breakdown between accounts/segments, not just a raw table. Build
"similar households / similar accounts / similar portfolios" (extending the existing similar-
advisors capability) if this doesn't exist yet.

**AGP Goals & Coaching**: Add real KPI gauges/meters (visual, not text). All charts get legends.
Real Goals & KPIs table: KPI name, Target, Current, Progress %, Status (on/off track, color-
coded). Program milestones with real Completed/In-Progress/Not-Started status. Coaching sessions
must show real per-advisor variation, not the same static content everywhere.

**Client Intelligence 360**: Rebuild the AI Recommendations card to the same structured standard
as the Insight/Coaching cards — must explain HOW the recommendation was reached (evidence,
sources), not just state it. Add similar households/accounts/portfolio comparisons.

**Coaching & Reviews**: Fix static/duplicate coaching-session data across advisors — real
variation. Build a real manager-facing feature: manager can add a coaching instruction/task
(selectable task list), persisted to the database, retrievable later with status, and available
as context to the AI Assistant/recommendations (real read path, not just storage).

**CRM Activities**: Build realistic, varied leads/referrals/opportunities (depends on 9.3's data
expansion). Fix the pipeline funnel visualization — diagnose what's actually wrong with it (a
funnel/stage chart, not whatever is currently rendering oddly); revisit further in a later
session if not fully resolved now. Add: upcoming activities/meetings/notes/tasks with
type/subject/who/when/status columns, a calendar view, activities grouped by type with icons,
and recent notes that genuinely vary per advisor.

**What-If Simulator**: Add "save as recommendation" — a manager can save a what-if scenario
result as a real recommendation against the advisor, with a category and a high-priority flag,
persisted through the real recommendations pipeline (not a separate fake table).

**Predictions & Forecasting**: Fix advisor-scoping (see 9.1). Beyond that: add real detail on
HOW each prediction was derived — the pipeline, the model/formula, the feature contributions —
this is one of the client's core "ML/DL" selling points and needs to look like it.

**Opportunities & Recommendations**: Fix advisor-scoping (9.1). Add: summary cards for total
accepted/completed/in-progress/rejected with counts, %, and green/amber/red color coding; a
revenue-impact-over-time graph; color-coded category tags with icons on each opportunity/
recommendation card; color-coded accept/reject buttons. **The "Learning state" section needs to
become a real, explained showcase of the RL feedback loop** — don't just show current weights;
add a simple simulation/explanation of how weights move with feedback over time so a client can
understand *why* the system gets smarter, not just that numbers change. This is explicitly one
of the two or three most important pages in the whole product per earlier direction — treat
accordingly.

**Recommendation Impact/ROI**: Fix static top-card values — must reflect the selected advisor/
scope for real (uses the same real feedback-learning data already proven elsewhere; this is a
wiring gap, not a missing-data gap).

**AI Assistant + Knowledge Hub**: Fix advisor-scoping (9.1) for AI Assistant. Restructure chat/
agentic responses to be readable — bulleted/sectioned, not one dense paragraph. Make the chat
input box larger and multi-line. Knowledge Hub answers get the same structured-card treatment:
answer / cited chunks / similarity scores as distinct, color-coded sections, not an
undifferentiated block.

**Feature Engineering Lab**: Fix advisor-scoping (9.1). Verify the underlying similarity/feature
computation is behaving correctly (re-run the same kind of cross-check verification used
throughout this build). Make the lineage section visual (a real diagram of source→feature flow),
not a text list.

**Explainability Explorer**: Fix advisor-scoping (9.1). This page needs real memory-timeline
content (currently effectively absent) and a more detailed, client-legible lineage chain —
enough that a client could follow "why did the system say this" end to end.

**Agent Orchestration & Observability**: The "Run Workflow" button currently does nothing.
Diagnose first — check whether this is the same frontend/backend networking issue from the
empty-page investigation (API base URL, server not running) before assuming it's a new
functional regression; this page was proven working earlier in the build. Fix whichever it
actually is, with real evidence, not an assumption either way.

### 9.6 New feature: Revenue Trend Explorer (new capability, can live in Revenue Analytics or as
its own page — decide during implementation, prefer extending Revenue Analytics if it fits
cleanly)

Bar chart of revenue over a user-selected date range and granularity (monthly/quarterly), sliced
by advisor / region / market / division / branch (user-selectable dimension). Below/alongside
each bar: an AI-generated summary of drivers for that period (reuse `get_llm_client()`, grounded
in real underlying data, same evidence standard as every other AI-generated card in this build),
and an explicit up/down indicator vs. the prior comparable period. This needs to look
presentation-quality — a client should be able to screenshot this for a deck. Depends on 9.3's
data expansion (needs enough real date range and dimensional variety to be meaningful).

### 9.7 Formatting corrections (mechanical, low-risk, can be done in parallel with anything above)

- Add missing `$` symbols wherever a dollar figure is displayed without one.
- Fix inconsistent title-casing across every header/title/section-title in the app — pick ONE
  convention (Title Case recommended for headers, matching most of the mockups) and apply it
  everywhere; audit systematically rather than fixing spot instances.
- Apply the green(positive)/red(negative) color-coding rule to EVERY numeric delta and
  up/down indicator across the whole app, not just where it currently exists — this should be a
  shared component/utility, not implemented ad hoc per page.

### 9.8 RAG corpus expansion

Test and expand the knowledge base with more real-world-style enterprise wealth-management and
AGP practice-management documents, across PDF/DOCX/PPTX formats (not just the current .txt-
sourced set) — exercise the real parsers built in Part 2A properly, with realistic document
volume and variety, not just enough to prove the pipeline works.

### 9.9 `.env` completeness

Produce a complete `.env.example` (and confirm `.env` locally) covering every configuration
value now in use: existing adapter modes/keys plus the new TigerGraph MCP tier's connection
variables (`TG_HOST`, `TG_GRAPHNAME`, `TG_USERNAME`/`TG_PASSWORD` or `TG_API_TOKEN`, etc., per
the tigergraph-mcp package's documented environment variables).

### 9.10 Model routing for this section

Given the volume and the client's explicit accuracy concern: use **Fable 5** for genuinely new
architecture/design work — the TigerGraph MCP adapter tier (9.4), the data model/schema
expansion (9.3), the RL learning-state explanation design (part of 9.5's Opportunities page), and
the Revenue Trend Explorer (9.6). Use **Opus 4.8** for the rest — the scope-following fix (9.1,
mechanical pattern-application), filter bar fixes (9.2), page component rebuilds that follow
already-established card/chart patterns (9.5's other items), formatting (9.7), RAG corpus
expansion (9.8, content work), and `.env` (9.9).

### 9.11 Execution plan — reasoned phases, dependencies, and safety rules

This replaces a first-pass ordering that under-thought two real risks: (a) the data-expansion
item has no natural stopping point and could consume an entire unattended session with nothing
else getting done, and (b) the new TigerGraph-MCP tier could get stuck fighting the same 2-core
hardware limit that already capped live query installs in Phase 2 — if unbounded, a single
stuck item can eat the whole run. The phases below are ordered by genuine dependency (what must
exist before what) and risk (bounded/certain work before open-ended/uncertain work), with
explicit guardrails on the two riskiest items.

**Model routing for this session: main thread on Opus 4.8, delegate 4 specific high-stakes items
to the `fable-architect` subagent (see `.claude/agents/fable-architect.md`).** This is a real
mechanism, not a workaround for not being able to run `/model` mid-session: Claude Code supports
custom subagents with their own model setting, invoked automatically by task match or explicitly
via the Task tool. Keep the main orchestrating thread on whatever model the session starts on
(Opus 4.8) for cost efficiency on the many mechanical/pattern-following items, and explicitly
delegate these four to the `fable-architect` subagent: 9.3 (data model/sample data design), 9.4
(TigerGraph MCP adapter architecture), the RL-learning-state explanation design inside 9.5's
Opportunities & Recommendations rebuild, and 9.6 (Revenue Trend Explorer design). When you reach
each of these four in the phase order below, use the Task tool to delegate to `fable-architect`
by name rather than doing the design work in the main thread.

**PHASE 0 — shared foundation (build once, reuse everywhere in Phase 3-4; do this first)**
- 9.0: replace the violet AI-accent color sitewide with the chosen non-purple alternative.
- Build ONE reusable delta-indicator component (icon + up/down arrow + %/point change,
  green/red) and ONE currency-formatting utility. Every subsequent page rebuild in Phase 3-4
  must use these, not hand-rolled formatting per page — this is the only way 9.7's color-coding
  rule ends up actually consistent instead of redone 15 times with small variations.
- First-pass title-casing sweep on pages that already exist (any NEW page built later in this
  session should just use correct casing from the start — no second full sweep needed at the end
  unless something slips through).
- **Fix the API-base-URL config properly, once, so the earlier empty-frontend bug cannot silently
  recur across a long session:** use a server-only (non-`NEXT_PUBLIC_`) env var pointed at
  `127.0.0.1:8000` for SSR and any internal tooling (Playwright, curl checks) — this is always
  correct from inside the container. Use a separate `NEXT_PUBLIC_`-prefixed var pointed at the
  actual public forwarded Codespaces URL for browser-side client fetches — this is what an
  external browser needs. Document both in `.env.example` (ties into 9.9). Confirm port 8000 is
  set to Public visibility in the Codespaces Ports panel. Verify both paths work: an internal
  curl/Playwright check AND a note of the exact public URL for the person to open in their own
  browser later.
- **Mid-session discipline for a run this long:** re-read the relevant Section 9 subsection at
  the start of each phase below, not just once at the start of the session — a session spanning
  many hours and many files should not rely on memory of a single early read.

**PHASE 1 — root-cause fixes (bounded, well-understood pattern, highest complaint density)**
- 9.1: scope-following fix on the 5 hardcoded pages (Predictions, Opportunities &
  Recommendations, AI Assistant, Feature Engineering Lab, Explainability Explorer) — the
  hierarchy/scope context already exists (Phase 11 Part 4), this is applying an established
  pattern, not inventing one.
- 9.2: filter bar (persistence across navigation, Time Period wiring, Compare-To selector,
  fix/clarify the refresh/search/alert icon buttons).
- Agent Orchestration "Run Workflow" button: diagnose BEFORE assuming a regression — check
  whether this is the same frontend/backend API-base-URL issue found during the earlier
  empty-page investigation (this page was proven working earlier in the build; a networking
  config issue reappearing is more likely than new breakage). Fix whichever it actually is.

**PHASE 2 — data foundation (gates several Phase 3-4 items; BOUNDED SCOPE, read the guardrails)**
- 9.3: data model + sample data expansion.
- **Guardrail 1 — do not silently invalidate prior verification.** A001, A020, and every other
  advisor whose figures are already cross-checked in PROGRESS.md/VERIFICATION_CHECKPOINT.md have
  real anchor numbers this entire build's credibility rests on. Expand data by ADDING new
  entities, date range, and variety — do not regenerate or mutate already-anchored advisors'
  underlying figures. If a genuine reason requires changing one, state exactly what changed and
  why, prominently, in PROGRESS.md — never let a previously-verified number silently drift.
- **Guardrail 2 — bounded target, not open-ended embellishment.** Define a concrete finish line
  before starting: e.g. expand the modeled date range to a specific number of months/years;
  expand each division to a specific number of additional branches/households with real-world-
  style names; add a specific number of additional varied CRM leads/referrals/opportunities.
  Pick reasonable concrete numbers and stop there — "richer data" has no natural end, so an
  explicit target is what prevents this phase from consuming the whole session.
- Schema changes (new vertices/edges/attributes) only where a specific Phase 3-4 requirement
  genuinely needs one — validate structurally (vertex/edge references resolve, manifest/CSV
  counts match) with the same rigor as the original foundation package audit, not by assumption.

**PHASE 3 — TigerGraph MCP adapter tier (highest implementation risk; BOUNDED EFFORT)**
- 9.4: build the 4-tier `GraphClient` (MCP → pyTigerGraph → RESTPP → Mock).
- **Guardrail — time-box Tier 1 specifically.** Build the adapter interface and all four tier
  implementations fully — that part is straightforward and low-risk. But actually getting the
  `tigergraph-mcp` server running live against this 2-core codespace's TigerGraph container is
  the uncertain part (this exact box already struggled with query C++ compilation in Phase 2).
  Attempt it once, reasonably. If it doesn't come up cleanly after a genuine but bounded attempt,
  do NOT keep fighting it for hours — fall back to documenting Tier 1 as implemented-but-
  unverified-on-this-hardware (same honest pattern as Phase 2's Section 8 finding), confirm
  Tier 2 (pyTigerGraph direct) works as the practical default, and move on. The architecture
  being correct matters more tonight than Tier 1 being proven live on underpowered hardware.

**PHASE 4 — page rebuilds (use Phase 0's shared components + Phase 2's expanded data)**
In this order — flagship first, then roughly the order most pages depend on Phase 2's data:
Executive Dashboard → Revenue Analytics (needs Phase 2's geographic/regional data) → Advisor 360
→ AGP Goals & Coaching → Client Intelligence 360 → Coaching & Reviews (includes the real
manager-assigns-task CRUD feature — this is a genuine new feature, not just a display fix, treat
it with the same rigor as any other new capability) → CRM Activities (needs Phase 2's realistic
lead/referral/opportunity data) → What-If Simulator (save-as-recommendation) → Predictions &
Forecasting (methodology/derivation depth) → Opportunities & Recommendations (including the
RL-learning-state explanation — this is a real design problem, give it real thought: how does a
non-technical client come to understand that the system's rankings improve from feedback? a
simple before/after or trend visualization of weight movement over recorded feedback rounds is
probably the right level, not a technical RL lecture) → Recommendation ROI → AI Assistant +
Knowledge Hub (response structuring, larger chat input) → Feature Engineering Lab (visual
lineage) → Explainability Explorer (real memory-timeline content, deeper lineage detail).

**PHASE 5 — new capability (needs Phase 2's data)**
- 9.6: Revenue Trend Explorer.

**PHASE 6 — independent content/config work (good filler if any earlier phase is blocked)**
- 9.8: RAG corpus expansion. Note: this needs WRITE capability for PDF/DOCX/PPTX, not just the
  read/parse capability built in Phase 2A — `python-docx`/`python-pptx` support writing already;
  PDF writing needs adding a library (`reportlab` or `fpdf2`) since only reading (`pypdf`) exists
  today. Add whatever's missing.
- 9.9: `.env.example` completeness for every adapter mode now in use, including the new MCP tier.

**PHASE 7 — closing verification (same discipline as every prior closure pass this build)**
Re-screenshot every page. Confirm: no purple remains anywhere, scope-following actually changes
displayed data when the advisor/scope selector changes (real test, not assumed), formatting
(currency/casing/color-coding) is consistent across all pages including the newly-built ones,
full boot check (backend imports, route count, frontend build).

**Standing rules for the whole session, restated for emphasis given its length:**
- Commit after every phase AND after every meaningful sub-item within Phase 4 (each page), not
  only at phase boundaries — a session this long needs frequent, small, resumable checkpoints.
- Update PROGRESS.md continuously, not just at the end of a phase.
- Do not stop to ask permission or wait for confirmation between phases or sub-items. Only pause
  for: a genuine blocker with no reasonable default (write it into PROGRESS.md, move to the next
  non-blocked item — don't just stop the whole session over one stuck item); or approaching a
  real usage/session limit (finish and commit whatever's in progress cleanly first).
- If every phase's well-defined work is exhausted before the session ends, re-read Section 9 in
  full and pick the next reasonable uncompleted item yourself rather than stopping — there is
  more real work listed here than one session will likely finish.

### 9.12 Mockup detail confirmations (from direct review of the "Wealth360" 15-panel grid and the
Hackathon flagship mockup — refines, does not replace, the 9.5 bullets above)

- **Recommendations page needs an inline Explainability panel**, not just a link to the separate
  Explainability Explorer: confidence % (e.g. "91%"), reasoning steps, key factors, and info
  sources shown directly alongside the selected recommendation.
- **Revenue Analytics has three distinct breakdown dimensions**, each its own chart: Revenue by
  Business Line (donut), Revenue by Channel (bar), Revenue by Region (map) — plus the trend line.
  Treat these as three separate required visualizations, not one generic "breakdown chart."
- **CRM Activities "Recent Meetings" table columns, exactly**: Date, Subject, With, Type,
  Outcome, Next Step. "Activities This Week" is a row of icon-labeled counts by type (Meetings /
  Calls / Emails / Tasks).
- **AGP "Goals & KPIs Detail" page structure**: a table row per goal/KPI (name, Target, Current,
  Progress %, Status with color coding) that drills into a detail view with a Target-vs-Actual
  bar chart over time, an AI-Generated "KPI Insights" recommendations block, and a "My Action
  Items" checklist.
- **Coaching & Reviews "Manager Reviews" section** shows the reviewing manager's identity (photo/
  name) alongside their review — reinforces that this page should respect the viewer's own
  persona/hierarchy level (a DDW/MDW manager reviewing "their" advisors), consistent with the
  scope-following fix in Phase 1, not just the advisor's own data.
- KPI cards throughout use a colored icon in a soft-colored circle to their left (not just a
  bare number) — confirmed directly in both mockups; apply via the Phase 0 shared component.

## 10. Industry-standard enhancements (expert additions, NOT part of tonight's Section 9 run —
future session candidates, reviewed and prioritized when the person is next available)

Section 9 was built almost entirely from the client's own literal feedback. This section adds
what real wealth-management and advisor-development platforms include that wasn't otherwise
requested — the goal is "award-caliber," not just "complete." Do NOT fold these into an
unattended overnight run without explicit confirmation — they're listed here so they're not
lost, and so the next planning conversation starts from a fuller picture, not to expand tonight's
already-bounded scope.

**Household-level intelligence (currently everything stops at advisor-level; real platforms go
one layer deeper into the actual client relationship. **Revised after Section 11 was planned:
these are now simple extensions of Section 11.1's model tier, not separate builds — implement
after 11, reusing its trained models rather than building parallel ones.**):**
- Household churn/attrition risk — extend the existing prediction pipeline (same pattern as
  advisor-level REVENUE_DECLINE_RISK) down to individual households.
- Next-best-product propensity per household, distinct from advisor-level opportunities.
- Book-of-business concentration risk: top-10-households as % of an advisor's total AUM.
- Review-cadence compliance: which households are overdue for their annual review.

**AGP-specific depth (the platform's namesake deserves the most industry texture):**
- Tiered cohort structure with visible progression (e.g. Associate → Certified → Senior), not
  just a flat score.
- Mentor/mentee pairing — a real structural element of advisor development programs. **Upgrade
  opportunity once Section 11's GNN embeddings exist:** pair mentors/mentees by embedding
  similarity plus capacity constraints, rather than arbitrary assignment. This specific matching
  algorithm design (a real constrained-matching problem) is Fable-appropriate; the pairing
  display itself is not.
- AGP program ROI: has an enrolled advisor's production grown faster since joining than a peer
  baseline? Likely the single most convincing evidence for a platform built around this program.
  **The peer-baseline methodology itself (what makes a fair comparison) is genuine statistical
  design work — Fable-appropriate, not a mechanical query.**

**Vulnerable-client / anomaly detection — MOVED to Section 11.1.** This is architecture-
specified (the Prediction & Recommendation Engine poster's own Model Strategy table names
"Isolation Forest / Autoencoders"), not a vague future idea — build it there, not here.

**Give the two already-flagged-as-broken header icons real purpose instead of just repairing
them:** the search icon becomes a real global search across advisors/households/documents; the
notification bell becomes a real feed (overdue reviews, AGP milestones hit, compliance flags).
Same implementation effort as a cosmetic fix, meaningfully more value.

**Executive-level polish real BI platforms have by default:**
- AUM net-flows waterfall (new AUM + organic growth − departures − fees) on the Executive
  Dashboard — the classic executive wealth-management chart, currently absent.
- Export any dashboard view to PDF/PPT — generalize the presentation-export capability already
  requested specifically for the Revenue Trend Explorer (9.6) to the whole platform.

**Lower priority / mention for completeness, not urgent:** Centers-of-Influence/referral-source
tracking as a CRM Activities extension; advisor succession-readiness tracking; fee/revenue-mix
transparency (fee-based vs. commission) per advisor. **AI model governance/audit-log page —
mostly subsumed by Section 11.11's Model Strategy table and AI Protections checklist once built;
only check for genuine remaining gaps here, don't rebuild what 11 already covers.**

When this section is prioritized in a future session (after Section 9 AND Section 11 are both
complete, per that ordering), run the same discipline as Section 9: real backend logic behind
every card, real evidence for every "done" claim, bounded scope per item before starting.
**Model routing for what remains here: `fable-architect` for the AGP ROI methodology and the
GNN-similarity mentor/mentee pairing algorithm specifically; everything else in this section is
Opus-appropriate.**

## 11. Production Architecture Alignment — real ML/DL/GNN/RL/FL ("make the dots connect")

**Sequencing: strictly AFTER Section 9's phases complete. Do not interleave with the Section 9
run.** Source of truth: the 12 architecture posters in `docs/spec/architecture/` (view them
directly before starting — High Level, Prediction & Recommendation Engine, Temporal Knowledge
Graph, PACE AI, Agent Orchestration, Context Engineering, Coach Q&A, Data & Knowledge Ingestion,
Evaluation & Trust, MCP Layer, Observability, Security & Governance).

**Why this section exists:** the client's core interest is seeing the production architecture's
intelligence layer — feature engineering → real predictions (ML/DL/GNN) → recommendations → RL
feedback, plus FL — actually working locally, dots connected. **Correction, now verified precisely
via a real traced call-graph check (not memory) as of the end of Section 9:** the LIVE
`/predictions` path is an additive weighted scorecard (`app/prediction/service.py`), NOT the
sklearn RandomForest. A real, working RandomForest DOES exist (`app/prediction/prediction_engine.py`
`LocalPredictionEngine`), but its only caller (`app/services/prediction_service.py`'s
`run_predictions()` — note the different, easily-confused module path,
`app.services.prediction_service` vs. the live `app.prediction.service`) is itself never invoked
by any router, agent tool, or context path. **Frame 11.1's prediction work correctly: this is
promoting a real, already-written, currently-dormant model to the live path for the first time —
not retraining a model that's currently serving.** Concrete tasks: decide scorecard-vs-model
precedence (the scorecard's own methodology text already advertises the RF as the "trained
alternative... when per-cohort training data is sufficient" — make that real, not just a string);
wire the model into the live endpoint/agent-tool path; ensure its output carries the same
contributions/evidence/reasoning-trace shape the scorecard already persists; train it on real
labels from Section 9's now-accumulated feedback history rather than a synthetic rank heuristic;
confirm training data volume is adequate on the real (now-expanded) dataset. Separately, there is
no GNN anywhere in the build — that gap is real and unchanged — and no household-level model, no
sequence/forecast model exist yet either.

**Feasibility already assessed — this is achievable on the 2-core box, unlike the TigerGraph
query-install wall:** PyTorch is already installed (sentence-transformers dependency). XGBoost
on the 100K+ row transaction/household data is trivial on CPU. A 2-layer GraphSAGE on a ~10K-
vertex graph via torch-geometric trains in minutes on CPU. A small GRU on 60 monthly revenue
sequences is trivial. **Honest small-data rule:** 60 advisors is too few samples for advisor-
level supervised training — train at household/transaction level (hundreds to thousands of
samples) and aggregate up; state small-data caveats plainly in model cards; never claim
production-grade accuracy from demo-scale data.

### 11.1 Real model tier — `ModelClient` adapter (same pattern as Graph/LLM/Embedding clients)

`MODEL_CLIENT_MODE=real|deterministic`, deterministic = the current verified scorers (kept as
fallback, never deleted). Real tier, corrected after direct research into TigerGraph's own
capabilities (do not hand-roll what TigerGraph already provides natively):

- **Classical graph algorithms — use TigerGraph's in-database GDS library, not a custom
  implementation, and each with a concrete, named purpose (no algorithm without a screen it
  serves):**
  - **Centrality (PageRank)** → a "Referral Network Position" indicator on CRM Activities and
    Advisor 360: identifies which advisors are key connectors in the referral network (highly
    connected, central to how referrals actually flow), shown plainly ("this advisor is a
    strong referral hub — connected to N other advisors' referral chains"). Feeds Section 10's
    AGP mentor selection: high-centrality advisors are natural mentor candidates, not an
    arbitrary pick.
  - **Community detection (Louvain)** → powers Section 10's AGP cohort structure directly: instead
    of arbitrary tiers, detected communities of advisors with genuinely similar patterns (book
    composition, growth trajectory) become the suggested cohorts, shown on the AGP Program
    Dashboard as "Peer Communities" with real membership — the tiering is discovered, not
    assigned by fiat.
  - **Similarity** (existing, being upgraded to GNN-based) → Similar Advisors/Households/
    Accounts panels, peer benchmarking.
  Install and run these exactly like the existing GQ-### queries (`INSTALL QUERY`/`RUN QUERY`,
  or via `pyTigerGraph`'s `Featurizer.installAlgorithm()`/`runAlgorithm()`). If a purpose can't
  be stated this concretely for something else on the poster's algorithm list, don't build it
  just because it's available — that's exactly the "Learning State" mistake from earlier in this
  build, repeated at the algorithm level instead of the UI level.
- **GNN — three tiers, in order of preference, not one hand-rolled implementation:**
  1. **`pyTigerGraph[gds]`** (the GDS extra: `pip install pyTigerGraph[gds]`) — this ships a
     built-in `GraphSAGEForVertexClassification` model class with `.fit()`/`.predict()`, plus a
     `neighborLoader()` that pulls features directly from live TigerGraph vertices into PyTorch
     Geometric format, with train/valid/test split utilities included. This is the correct,
     platform-native way to train a real GNN here — prefer it over a custom implementation.
     **Real dependency risk, stated plainly:** `neighborLoader` needs actual edge data loaded in
     the live local TigerGraph instance to sample neighborhoods, and Phase 2's finding was that
     full edge load stalls on this 2-core box. Before starting this tier, attempt a bounded,
     narrower edge load — only the specific edge types GraphSAGE actually needs (advisor↔
     household, household↔account, advisor↔opportunity, etc.), not all 126 types — time-boxed,
     same hardware-guardrail discipline as Phase 3's MCP adapter.
  2. **Local PyTorch Geometric GraphSAGE as fallback** — if tier 1's live edge load doesn't come
     up cleanly, build the same GraphSAGE architecture trained against an in-memory graph
     constructed from `MockGraphClient`'s full edge data (the mock store already has all 126
     edge types / 109K+ rows in Python memory, even when the live engine doesn't). This is not
     an inferior fallback — same model, same real training, just not using TigerGraph's native
     loader. State clearly in the model card which path was actually used.
  3. Deterministic feature-projection (current) — final fallback only if both above fail.
- **Vector storage — clean split by data domain, no overlap, no "which one wins" ambiguity
  (confirmed final):**
  - **Chroma stays exactly as-is, untouched, for document/RAG vectors only** — playbooks,
    policies, knowledge base chunks. This is already built and extensively verified across
    multiple checkpoints; no migration, no side-by-side trial, nothing to prove here. Out of
    scope for this section entirely.
  - **TigerGraph-native vector storage handles every ML/feature-engineering/GNN vector.**
    Confirmed real via TigerGraph's own published research (TigerVector, SIGMOD 2025) and live
    GraphStudio 4.1+ docs: a genuine `EMBEDDING` vertex attribute type with HNSW indexing, GSQL
    extended with native vector search including hybrid graph+vector queries in one query (e.g.
    "similar to X AND connected to Y" natively). Use this for advisor/household/portfolio
    embeddings, GNN output, and any learned representation of a graph entity — build a
    `TigerGraphVectorClient` (same Section-2 adapter pattern) as the one real implementation for
    this domain; a deterministic fallback (current feature-projection similarity) covers the
    case where the local install doesn't support it, same pattern as every other adapter here.
  - **Verify empirically before building on it, don't assume version support:** confirm the
    local TigerGraph Community Edition 4.2.3 container actually supports `EMBEDDING` attributes
    — same "attempt it, document honestly what actually works on this hardware/version"
    discipline already used for the MCP tier and the edge-loading limitation.

- **Retrain the existing RandomForest (or upgrade to XGBoost/LightGBM) on real feedback-loop
  labels** for the two existing risk predictions (REVENUE_DECLINE_RISK, AGP_OFF_TRACK_RISK) —
  replacing the original synthetic rank-heuristic training target with real recorded outcomes,
  now that enough exist. Add a new household-level churn propensity model (genuinely new). Real
  SHAP feature contributions replace the current hand-computed contribution bars on the
  Predictions page (real SHAP values, same UI pattern) — verify before/after: same advisor,
  contribution values before (synthetic-label model) vs. after (real-label model).
- **Small sequence model (GRU/LSTM)** on monthly revenue series → a real forecast line (with
  uncertainty band) on Predictions/Revenue pages.
- **Anomaly detection (Isolation Forest, or an autoencoder) — promoted here from Section 10,
  not left as a vague future idea.** The Prediction & Recommendation Engine poster explicitly
  names "Anomaly Detection: Isolation Forest / Autoencoders" as a model type — this is
  architecture-specified, not invented. Use it for the vulnerable-client detection concept from
  Section 10 (unusual withdrawal patterns, activity inconsistent with a household's own history)
  — the model fitting itself is mechanical (Opus-appropriate), but delegate the feature
  selection and the responsible, non-alarmist presentation design to `fable-architect`, same
  reasoning as the RL-explanation delegation.
- **Model registry + model cards page, and Model Strategy/AI Protections/Evaluation sections —
  build these as new tabs/sections WITHIN the Admin page Section 9 already rebuilds, not as
  separate new pages.** Real reuse, not just tidiness: avoids 2-3 redundant page shells.
  Registry: every model's name, version, algorithm (including which GNN tier actually ran),
  training date, training-data description, metrics, feature list, small-data caveats. Training
  runs persist artifacts to disk (`models/artifacts/`, gitignored) with a committed metrics/
  registry JSON.
- Training must be re-runnable via one script per model; time-box GNN training epochs sensibly
  for the 2-core box; cache artifacts, don't retrain on every boot.
- **Reuse points from Section 9 — check these before building anything new, don't duplicate:**
  the Phase 0 shared formatting components; 9.3's expanded sample data as the training data
  (check its outcome-variety is sufficient before generating more); 9.4's live pyTigerGraph
  connection tier (extend for the `[gds]` extra rather than reconnecting separately); the
  Opportunities & Recommendations page for the RL/feedback visualization (11.2/11.3); the
  Explainability Explorer for the context-pipeline trace (11.6); the AI Assistant/Knowledge Hub's
  restructured citation cards for reranking scores (11.6) — extend each, do not rebuild.
- **Precision on features vs. embeddings, since this determines how the pipeline connects:** the

  33 named, interpretable Feature_Catalog features (Phase 5, already built) are the INPUT — both
  as columns for the XGBoost tabular models and as node-feature vectors for the GNN. The GNN's
  OUTPUT — its learned embeddings — is the actual dense vector, stored per the Chroma decision
  above. Features and embeddings are not the same thing; don't conflate them in the UI or docs.

### 11.2 RL formalization (extends the already-verified feedback loop — do not rebuild it)

Formalize the existing weight-update mechanism as a documented contextual bandit: state
(advisor feature snapshot), action (recommendation family), reward (accept/complete positive,
reject negative — document the exact values already in use), update rule. Feed this into the
Section 9.5 learning-state explanation rather than duplicating it. Add a replay visualization:
weight trajectory over the real recorded feedback history.

### 11.3 FL = Feedback Loop (corrected — this is NOT Federated Learning; do not build FedAvg)

**Correction from an earlier draft of this section, which misread "FL" as Federated Learning.**
The client's actual meaning, confirmed directly: recommendations get simulated through to a
recorded outcome (successful or unsuccessful), and that outcome should feed back into the GNN's
learned knowledge — not just the existing bandit-weight multiplier — so the system doesn't keep
surfacing the same kind of unsuccessful recommendation. This is a real, well-established pattern
(reinforcement learning for recommender systems using human accept/reject signal as reward,
conceptually adjacent to RLHF but applied to a recommendation policy rather than an LLM) — build
this, not a federated-learning simulation.

**Design, additive to the already-verified bandit system, not a replacement for it:**
- Keep the existing weight-multiplier mechanism exactly as-is — it's real, verified, and is the
  simple, visible layer most users will actually watch move.
- Add a deeper layer on top: recorded outcomes (accept+completed+positive business impact = a
  positive label; reject or completed-with-negative-impact = a negative label) become training
  signal for periodic GNN embedding fine-tuning — e.g. a contrastive-style objective that pulls
  together the embeddings of entities (advisor/household/opportunity-type combinations) that
  co-occurred in successful outcomes, and pushes apart those from unsuccessful ones. Framed
  simply: the graph's "sense of what similar situations look like" should shift based on what
  has actually worked, not stay static after initial training.
- Build a live "Run Feedback-Driven Retraining" control: show a recommendation/similarity result
  BEFORE incorporating a batch of recorded outcomes, run the update, show it AFTER — a visible,
  honest demonstration of the loop, using real recorded feedback history, not staged data.
- **Data requirement, ties to 9.3/11.1's data expansion:** this needs real OUTCOME VARIETY —
  a meaningful number of both successful and unsuccessful recorded outcomes across different
  recommendation families, not uniformly-positive sample data. Extend the sample-data generator
  to produce a realistic mix of both, with enough volume that the retraining step has genuine
  signal to learn from.
- Terminology note for any client-facing copy: describe this as "outcome-driven learning" or
  "the feedback loop," matching the poster's own "Outcomes Driving Learning" framing — avoid
  calling it Federated Learning or RLHF in exact technical terms, since neither is precisely
  what's being built; both are reasonable conceptual analogies, not literal descriptions.

### 11.4 Temporal knowledge graph showcase (capability exists in fragments — surface it)

Point-in-time queries ("as-of" date selector) on the Feature Engineering Lab (compare feature
snapshots across dates — versioned snapshots already exist), and a temporal traversal demo in
Graph Explorer (entity state/relationships as of a chosen date). Connect the existing Memory
Timeline to this story explicitly.


### 11.5 Evaluation & Trust layer (currently absent entirely; the poster most likely to impress
an AI-governance-minded client)

- Golden dataset: 20-30 curated Q&A pairs with expected grounded answers/citations, committed
  as a versioned file.
- Eval harness: one command runs the golden set through the real Coach Q&A path and scores
  groundedness (does the answer cite retrieved chunks/graph facts that actually support it),
  citation coverage, and refusal-correctness (the no-match honesty case already verified once).
- Results page: latest eval run's scores, per-question pass/fail, trend across runs. Wire the
  hallucination-guard principle visibly: answers must trace to retrieved evidence.

### 11.6b Graph relational reasoning — BUILT (2026-07-07, supersedes the "flat bundle" gap)

The context assembler no longer assembles a flat bundle: for every AI answer it now performs
GENUINE graph-traversal relational reasoning (the core purpose of the temporal knowledge graph),
wired into the live chat/agentic path and visible in the Explainability Explorer:
- **Reasoning-trace reuse (experience memory):** each answer records a `phx_dm_reasoning_trace`
  anchored to the advisor via the new `phx_dm_reasoning_for_advisor` edge; before answering, prior
  traces for that advisor are retrieved BY TRAVERSAL (`get_reasoning_traces_for_scope`) and fed in,
  so the agent builds on past conclusions.
- **Multi-hop traversal:** `advisor_reasoning_traversal` walks advisor → households → open
  opportunities, and advisor → `phx_dm_advisor_has_similarity_match` (scores) → similar advisors →
  their proven action families (recs / impact-ledger / outcomes). `scope_reasoning_traversal` walks
  scope → advisors → households → aggregated outcomes with named contributors.
- Implementation: `app/graph/queries/reasoning.py` (instrumented mock traversals + GSQL
  GQ-048..050), `app/ai/reasoning/graph_reasoner.py`, a force-kept `GRAPH_REASONING` context item,
  and the `/explainability/graph-reasoning/{scope}/{id}` endpoint + `GraphReasoningPath` UI panel.
- Rule preserved: **traversal is real and instrumented (the actual entities visited are returned),
  never LLM-narrated.** Verify graph-reasoning behavior with `LLM_CLIENT_MODE=claude`.

### 11.6 Context engineering pipeline — memory coverage audit + real ranking (not just visibility)

**Standing rule for this entire section, stated once, applies everywhere below:** any
verification of AI-*generated behavior* — grounding quality, continuity, structured-response
formatting, reranking effectiveness, RAG answer quality, scope-level reasoning — MUST use
`LLM_CLIENT_MODE=claude` (real API calls), never mock. Mock output is deterministic/templated by
design and cannot demonstrate genuine reasoning; it's fine for pipeline-wiring/data-correctness
checks where the LLM's actual prose isn't what's being tested, but not for anything claiming to
prove the system is actually intelligent.

**Persona/hierarchy-scope-aware AI reasoning — real gap, not yet built or tested.** The Section 9
scope-following fix uses a hook literally named `useScopedAdvisor`, which by design resolves any
hierarchy scope down to one representative advisor. That's proven correct for advisor-level
questions. It has never been tested — and is very likely NOT yet capable — of handling a genuine
rollup-level question: an MDW asking about their advisors broadly, a DDW asking "why is my
division's revenue down" or "which of my advisors need attention," where a correct answer
requires reasoning across ALL entities in that scope, not resolving to a single one. The
underlying capability already exists (`ScopeRollupService`, built for the Executive Dashboard,
does real aggregate reasoning across many advisors) — extend the AI Assistant/agentic context
assembler to consult it (or an equivalent rollup query) whenever the active persona/scope is not
Advisor, instead of defaulting to one resolved advisor. Build this before claiming the AI
Assistant is scope-complete.

**Multi-turn continuity + scope-level reasoning test — combined, using real Claude, before
building anything further:**
1. Advisor-level: ask a real question for one advisor, confirm the turn is written to memory,
   ask a natural follow-up that only makes sense given turn 1 without restating it, show the
   actual assembled context for turn 2, confirm the real answer correctly builds on turn 1.
2. Division/rollup-level: switch scope to a Division (DDW persona), ask "why is my division's
   revenue down this quarter" or equivalent. Show the actual assembled context — does it contain
   aggregated/multi-advisor data, or does it silently fall back to one advisor? Confirm the real
   answer names actual contributing advisors/figures across the division, not one advisor's
   story presented as if it were the whole division's.
3. Both tests: real command output, the real answers, the real context payloads — not a status
   claim. If either doesn't work today, fix it as part of this section.

The Temporal Knowledge Graph poster specifies 6 memory types per persona: Conversation,
Reasoning, Semantic, Episodic, Procedural, Preference. **Audit first, don't assume:** which of
these 6 are actually written to and read from today, versus schema-present but never populated?
Based on what's verified so far, Conversation and Reasoning memory are real and active; Semantic/
Episodic/Procedural/Preference are very likely schema-only. Close real gaps found — populate and
exercise every memory type the poster specifies, not just the two already proven.

**Retrieval must be genuinely relevance-ranked, not a naive fetch-everything-of-type-X.** The
poster's pipeline explicitly includes a "Context Ranking (Cohere Rerank)" step that does not
exist in this build today — context assembly currently concatenates by source type, not by
relevance. Add a `RerankClient` adapter (same Section-2 pattern): a local default (e.g. a
cross-encoder or the existing embedding cosine-similarity as a rerank proxy — free, no new
vendor) and a real Cohere Rerank option matching the poster's named tool, selected via
`RERANK_CLIENT_MODE=local|cohere`. Apply it to context assembly across chat, agentic, and RAG —
this is what "the agent should be intelligent enough" to do: retrieve broadly, then rank and keep
only what's actually relevant to the current question/persona/scope, not everything available.
**This directly serves the continuity test above too**: as an advisor's conversation history
grows, ranking is what keeps a relevant recent exchange from getting diluted by old, unrelated
ones — without it, "remembers everything" can mean "remembers nothing usefully."

Once memory coverage and real ranking are in place, make the pipeline VISIBLE per the poster:
for any AI answer, an expandable trace showing resolved persona → hierarchy scope → time window
→ retrieved context items (with sources and rank scores) → pruning/compression decisions → final
prompt assembly. Extend the Explainability Explorer rather than building a new page.

### 11.7 Observability depth

Per-request stage-latency trace (the Hackathon mockup's bottom "SYSTEM TRACE" bar is the target
visual), token/cost tracking per LLM call (real counts from the Claude adapter; estimated for
mock), agent-step timeline on the Agent Orchestration page. Extend the Admin/observability
surface.

### 11.8 MCP layer completion

Section 9.4's 4-tier GraphClient covers graph access. Per the MCP poster, additionally expose
feature-store lookups and model-serving (predict for advisor X) as MCP tools where feasible, so
the agent layer's tool registry matches the poster's shape. Bounded: registry + the two tool
families, not an exhaustive tool catalog.

### 11.9 Model routing and guardrails for this section

- `fable-architect` subagent (by name, via Task tool): 11.1 model design/training approach,
  11.3 FL simulation design, 11.5 eval harness design. Main thread (Opus): all wiring, pages,
  registry plumbing, 11.4, 11.6, 11.7, 11.8.
- Same data guardrail as 9.3: training on expanded data must not mutate the anchored, verified
  advisor figures. Same evidence bar as the whole build: every model's "trained" claim comes
  with real metrics output; every page change with real screenshots.
- Hardware guardrail: if any training step exceeds a sensible time-box on the 2-core machine,
  reduce scale (fewer epochs, smaller hidden dims, sampled subgraph) and document the reduction
  honestly — never fake a metric to look better, and never let one stuck training run consume
  the session (same rule as the Phase 3 MCP time-box).

### 11.10 Poster placement

The 12 architecture posters must be committed to `docs/spec/architecture/` before this section
starts, so they can be viewed directly during implementation — do not work from a text summary
of them.

### 11.11 Make the architecture's own story visible in the product (new insight from reviewing
all 12 posters together, not covered elsewhere)

The architecture frames this as **"Two AI Systems, One Enterprise Platform"** — the proactive
system (insights, predictions, recommendations, delivered automatically; the architecture
posters' internal name for this is "PACE AI" — in the actual product, label it **"iPerform
Insights and Coaching"**) and the reactive system (Q&A and coaching, user-initiated; the
posters' internal name is "iPerform Coach" — in the product, label it **"iPerform Coach Q&A
Assistant,"** including on the AI Assistant page itself, not just as a small badge).
anywhere — everything reads as one undifferentiated "AI Assistant." Making this explicit is a
low-effort, high-payoff change for a client evaluating whether the demo matches their own
architecture vision:

- **Correction (client-directed, overrides the original wording below): the individual "✦ AI
  Generated" chip on cards stays exactly "AI Generated" — do not replace it with a product name.**
  Apply "iPerform Insights and Coaching" (proactive) / "iPerform Coach Q&A Assistant" (reactive)
  at the nav/page/section level only — e.g. a small persistent label in the page header or nav
  grouping indicating which of the two systems that page belongs to — never on the per-card AI
  chip itself, which is a different, smaller piece of UI serving a different purpose (marking
  content as AI-generated, not branding which system produced it).
  Small UI change, large "this matches exactly what we designed" recognition effect.
- Every poster has a **"Model Strategy (Per Function)"** table naming which model handles which
  job. Add a real equivalent to the Admin/Observability page: for the current session, which
  actual model/adapter served each function (Insight Agent → Claude/mock, Prediction Agent →
  XGBoost/deterministic, etc.) — ties the demo's real behavior directly back to the client's own
  documented design, reinforcing "this is your architecture, actually running."
- Every poster lists **"Top 10 AI Protections."** A simple, honest status checklist (implemented
  / partial / not yet) on the Admin page turns the client's own governance framework into a
  visible trust artifact inside the demo, rather than something that only exists on a poster.
- Every poster lists **Business Outcomes** (Increase Revenue, Increase NCF, Increase AUM,
  Improve Goal Attainment, Increase Advisor Productivity). Annotate the Executive Dashboard's
  KPIs with which business outcome each one maps to — connects the technical build back to the
  client's own stated business case in their own language.

Bounded, mechanical, high-recognition-value — good candidate for early in Section 11 or even
folded into Section 9's remaining page work if time allows, since none of it depends on the new
ML/GNN work landing first.

## 12. Regression Audit & Critical Fixes (client review after Section 11)

**MASTER EXECUTION ORDER for this unattended run — follow exactly, do not reorder:**
**Section 12 → Section 13 → Section 13B → Section 10 (remaining items only) → Section 14.**
Rationale: fix the broken foundation (12) before building the stateful loop (13) before building
the narration over that loop (13B) before the remaining enhancements (10) before flipping to
real-mode for handover (14). Commit after every numbered sub-item. Update PROGRESS.md
continuously. Push to origin at every section boundary at minimum. Do NOT stop for routine
check-ins or approval between items or sections — only pause for a genuine blocker with no
reasonable default (document it in PROGRESS.md, move to the next non-blocked item) or an
approaching usage limit (finish and commit the current item cleanly, then stop). If a whole
section's well-defined work completes, continue straight into the next section per this order
without waiting. This is a long run intended to complete unattended overnight; expect it to span
the full session.

**Standing evidence rule (unchanged, restated because it is the thing that prevents wasted
work): every "done" claim needs real evidence — real before/after values, real screenshots, real
command output — never a status assertion alone. Every AI-behavior check uses real Claude
(`LLM_CLIENT_MODE=claude`), never mock. Diagnose root cause before fixing; state for each item
whether it was a Section 11 regression, an original never-closed gap, or a clarification.**

**Context, stated plainly so the reason for this section is understood, not just its task list:**
several things previously built and verified working in Section 9 (filters, scope-following,
specific dashboard components) are now reported broken or missing after Section 11's substantial
backend changes (model tier promotion, GNN, MCP layer, reranking). Some items were never fully
built despite being specified. **Diagnose each item's actual root cause — genuine Section 11
regression vs. an original gap that was never closed vs. a clarification needed — don't assume;
state which one it is for each fix, with real before/after evidence, same bar as every other
verification in this build.**

### 12.1 Executive Dashboard
- Filter bar: hierarchy drill-down (division/region/market) intermittently not appearing; Period
  and Compare-To controls not functioning — diagnose whether Compare-To ever had real backend
  logic behind it or was UI-only. Add an explicit **"Reset filters"** control that returns to the
  default scope/period cleanly.
- Add the still-missing components from the Hackathon mockup, specifically: Revenue Trend chart,
  Revenue by Product Category, Revenue Drivers (vs Prior Year), Benchmarking (vs Peers), Top/
  Bottom Markets. Add the AI Insight Summary card (grounded in the currently filtered scope/
  period's actual retrieved values, not static) and the AI Coaching Card (Advisor persona only —
  do not show it when scope is Firm/Division/Region/Market).
- Remove the Business Outcomes section entirely (client-directed).
- Add a real **Bottom Advisors** table alongside Top Advisors (not just "Needs Attention" under
  a different framing — an explicit bottom-by-revenue list), and add more real detail to both
  (not just a name and a number — the specific reason, and at least one supporting figure).

### 12.2 Filter bars generally
Audit every page's filter bar, not just Revenue Analytics (reported as having none at all) —
this needs a page-by-page pass, since Section 11's changes may have broken the shared filter
components on some pages while leaving others intact. Fix each with real before/after evidence
(same filter, different scope/period selection, visibly different data).

### 12.3 Revenue Analytics
- "Revenue by scope" empty, Revenue Trend graph broken — diagnose against the filter-bar audit
  above; likely the same root cause, not two separate bugs.
- **Replace the tile-grid state cartogram with an actual geographic map** — real US state shapes
  (e.g. `react-simple-maps` or an equivalent real US TopoJSON/GeoJSON), not an abstract tile grid.
  The client's feedback is explicit: "not some boxes with state names" — take this as a hard
  requirement, not a style preference to weigh.

### 12.4 Advisor 360 / Client 360
- **Fix the "Referral Network Position" (centrality) section's clarity** — it currently shows a
  score with no clear meaning attached. This is exactly the failure mode Section 11.1 was
  explicitly written to avoid ("no algorithm without a screen it serves") — the purpose exists in
  the plan but didn't survive into the actual UI copy. Add plain-language interpretation directly
  in the card (what the number means, why it matters, e.g. "this advisor is a top-15% referral
  connector — a strong mentor candidate"), not just a labeled number.
- The "Households (N) · Accounts (N) · Activities (N)" section still shows only a households
  table — add the accounts split and segment breakdown that was specified back in Section 9.5
  and evidently never actually built. Verify it's real after building, don't just claim it.

### 12.5 CRM Activities
Redesign the Pipeline by Stage visualization to a more standard, polished funnel treatment —
the current CSS-band approach functions correctly (verified in Section 9) but doesn't meet the
visual bar. This is a design pass, not a logic fix.

### 12.6 Advisor-selector dropdown — add directly on these pages, don't rely solely on the
breadcrumb (belt-and-suspenders fix for a repeatedly-raised concern)
Predictions & Forecasting, Opportunities & Recommendations, Feature Engineering Lab, and
Explainability Explorer were verified scope-following in Section 9 (real Playwright evidence,
different advisors, different data). If they now read as "flat, A001-only" — diagnose whether
this is a genuine Section 11 regression to the shared scope hook, or a discoverability problem
(the hierarchy breadcrumb doesn't read as an advisor selector to someone testing quickly). Fix
the root cause AND, regardless of which it is, **add an explicit, visible advisor-selector
dropdown directly on each of these four pages** — removing any ambiguity going forward, even if
the breadcrumb technically already works.

### 12.7 Feature Engineering Lab — re-verify against Section 11's changes specifically
Confirm every component still reflects real values after the Section 11 model/GNN/feature
pipeline changes — don't assume Section 9's verification still holds after that much underlying
change. Re-run the same kind of live cross-check used throughout this build (real feature values,
real lineage, real similarity) against the current, post-Section-11 pipeline specifically.

### 12.8 Opportunities & Recommendations — button actions need a visible consequence, not just
an internal learning-signal update (real gap, directly sets up Section 13 below)
Clicking Accept/Complete/Modify/Ignore/Reject currently only updates an internal learning signal
with no visible change — the client cannot tell anything happened. At minimum for this section:
the recommendation's status must visibly update, the accepted/completed/rejected counts must
visibly change, and a "what changed" note must appear. **Full state-machine behavior (disabling
buttons post-terminal-status, generating a real impact, cross-screen propagation) is Section 13,
not here** — this subsection is the minimum visible-feedback fix; Section 13 is the full loop.

### 12.9 Admin — Health / Observability tabs
Two Next.js errors reported — reproduce and fix with real error output, not a guess.

### 12.10 Navigation / branding
- Clarify or redesign the bottom-left "Advisor, Firm, YTD" element — if it's the persona/scope/
  period summary, label it clearly as such; if its purpose can't be stated plainly, redesign it.
- **Rename the firm entity to "Chase Wealth Management"** — update the actual seed-data Firm
  vertex's name, not just a UI label, so it's consistent everywhere it's referenced (hierarchy
  breadcrumb, Executive Dashboard, any firm-scoped text).

## 13. End-to-End Stateful Recommendation Lifecycle (genuine new architecture — delegate the
design to `fable-architect`; this is not a bug fix, treat it with the same rigor as Section 11)

**What this section exists to solve, in the client's own words:** the system needs to
demonstrably work end-to-end as a live cycle, not a set of static pages that each independently
look correct. Select an advisor → see real recommendations → accept one → see a clear, visible
record of what changed and why → mark it completed → a real simulated consequence occurs (e.g. a
transaction/impact tied to that specific action) → the recommendation's buttons disable
appropriately for its new terminal status → the change is visible across OTHER screens (Advisor
360, Revenue Analytics, Executive Dashboard) → asking the AI Assistant about this advisor
afterward reflects the new state ("you completed X, here's the measured impact") → new
recommendations can be regenerated → the cycle continues. This is the single most important
remaining piece of this build — it's what turns a demo into evidence that the *system*, not just
its pages, actually works.

### 13.1 Recommendation state machine (real, not cosmetic)
Formal states: `OPEN → ACCEPTED → IN_PROGRESS → COMPLETED` (terminal) or `OPEN → REJECTED`/
`IGNORED` (terminal) or `ACCEPTED → MODIFIED → (re-enters OPEN or ACCEPTED)`. Persist status
transitions with a timestamp and an actor (advisor or "system/agent"). Once a recommendation
reaches a terminal status, its action buttons must disable in the UI — verify this concretely,
not just claim it status-checks correctly.

### 13.2 Real simulated impact on completion
When a recommendation is marked COMPLETED (by the advisor or, per the client's suggestion, by an
agent that can also complete it and leave a note): generate a real, persisted consequence tied
to that specific recommendation — e.g. a new transaction record reflecting the recommendation's
projected impact (using the recommendation's own real estimated-impact figure as the basis, not
an arbitrary number), linked by a real edge back to the recommendation that caused it. This is a
genuine "impact ledger" entry, not a UI-only status change. Log a clear, human-readable "what
changed" note on the recommendation itself (e.g. "Completed 2026-07-06: managed-account review
conducted, +$X,XXX revenue impact recorded").

### 13.3 Cross-screen propagation — the change must actually be visible elsewhere
After a completion event, the SAME advisor's data on Advisor 360, Revenue Analytics, and the
Executive Dashboard's rollup must reflect the new transaction/impact — not require a full data
regeneration to show up. Verify concretely: complete a recommendation, then load each of those
three pages fresh, and show the real before/after numbers differing by exactly the recorded
impact amount.

### 13.4 AI Assistant awareness of the new state
After a completion event, ask the AI Assistant about this advisor. The real answer must
reference the completed recommendation and its measured impact — this depends on the context
assembler picking up the new transaction/impact record and the recommendation's updated status,
not just the original static feature snapshot. Verify with a real Claude call and the real
before/after answer text, same as every other AI-behavior check in this build.

### 13.5 Regeneration cycle
After a completion event, allow regenerating recommendations for that advisor — verify the newly
generated set reflects the changed state where relevant (e.g. if the completed action addressed
a specific opportunity, that opportunity should no longer generate the same recommendation
again, or should be marked addressed).

### 13.6 Explainability, still required for every recommendation in this loop
Every recommendation, at generation time, must have a clear "how we arrived at this" section
with real evidence (features, predictions, opportunities, playbook) — this already exists
elsewhere in the build (Section 9's rebuilt Explainability/lineage work); make sure it's
genuinely present for recommendations moving through this new lifecycle too, not lost in the
new state-machine wiring.

### 13.7 Model routing
Delegate the overall design (state machine shape, impact-generation logic, propagation strategy,
context-assembler integration) to `fable-architect` (via the proven general-purpose-subagent-
with-`model:"fable"`-override workaround) — this is genuine system design, not a mechanical
extension of an existing pattern. Main thread (Opus) does the wiring, UI, and page integration
once the design is set.

### 13.8 Verification bar
This section is not done until the full cycle has been demonstrated with real evidence in one
continuous trace: select advisor → real recommendations shown → accept+complete one → real
impact recorded → buttons disabled → three other pages show the change → AI Assistant reflects
it → regenerate → new recommendations shown. Screenshot or log every step. This is the headline
proof of the whole build — treat the verification with matching seriousness.

## 13B. Guided End-to-End Story Mode (the deep-think answer — industry-standard demo narrative,
NOT just the button-click loop of Section 13; delegate design to `fable-architect`)

**Why this exists — reasoned from what enterprise wealth-tech demos actually need to win, not
just from the literal request:** Section 13 makes the recommendation loop genuinely stateful.
But a buyer evaluating a platform doesn't experience "state" — they experience a *story they can
follow*. The single most common failure of a feature-complete demo is that every screen works in
isolation and no one can narrate how they connect. Award-caliber demos solve this with a guided,
observable journey: one triggering event, followed visibly through every layer, ending on a
measurable business outcome the buyer cares about. This section builds that narration layer on
top of the real system — it does not fake anything; it makes the real end-to-end flow *legible*.

### 13B.1 A "How It Works" / pipeline-trace view for any AI output
For any insight, prediction, recommendation, or answer, the user can open a step-by-step trace
showing the real journey that produced it, as a horizontal flow a non-technical person can read:
**Data (which graph entities/facts) → Feature Engineering (which features, real values) → Model
(which model/algorithm, real score + confidence) → Opportunity/Recommendation (what was derived)
→ Context & Compliance (what was retrieved, what was checked) → Delivered Output.** Each stage
shows the real artifact from that stage (real feature values, real SHAP contributions, real
retrieved chunks, real compliance verdict), with real per-stage timing (the Hackathon mockup's
"SYSTEM TRACE" bar is the visual target). This turns the architecture posters' pipeline diagram
into something the client can watch execute on real data. Extend the Explainability Explorer and
the 11.6 context-trace work — do not build a disconnected new page; this is the same lineage
data, presented as a legible left-to-right story.

### 13B.2 A guided scenario walkthrough (the headline demo artifact)
Build one flagship, replayable, end-to-end scenario a presenter (or the client alone) can step
through, each step landing on the REAL screen with the REAL data — not a slideshow, the actual
app driven through a scripted path:
1. **Trigger**: an advisor's revenue decline is detected (real prediction on real data).
2. **Diagnosis**: the AI Insight explains *why*, grounded in real drivers (real feature values).
3. **Prediction & risk**: the real model score, contributions, confidence.
4. **Opportunity & recommendation**: the real next-best-actions derived from it, with real
   estimated impact and the real explainability chain.
5. **Compliance**: the real compliance check on the recommendation.
6. **Action**: accept + complete the recommendation (the real Section 13 state machine).
7. **Impact**: the real simulated consequence recorded (Section 13.2 impact ledger).
8. **Propagation**: the same advisor's Advisor 360 / Revenue / Executive rollup now reflect it
   (real Section 13.3 cross-screen change).
9. **Learning**: the feedback loop / GNN update reflects the outcome (real Section 11.2/11.3).
10. **Closure**: ask the AI Assistant about the advisor — it references the completed action and
    measured impact (real Section 13.4).
Implement as a guided overlay/checklist that navigates the real app and highlights what to look
at on each real screen — every step must show real data from the real backend, never a canned
illustration. This is the single artifact most likely to make the demo land as "we saw the whole
system actually work, end to end."

### 13B.3 Persona-journey coverage (industry standard: show it works for every buyer in the room)
The guided scenario above is advisor-centric. Add at least one rollup-persona equivalent so a
DDW/MDW evaluator sees their own journey: a division-leader story — detect an underperforming
segment across the division (real cross-advisor rollup reasoning, Section 11.6) → drill into
contributing advisors (real data) → a coaching/AGP action at the division level → visible impact
on the division rollup. Reuses the same real pipeline; different entry scope. Confirms the "any
persona can ask about their scope" capability is real, not advisor-only.

### 13B.4 A business-impact / ROI summary view (industry standard: close on the money)
A view that aggregates, from real recorded outcomes (Section 13.2 impact ledger + the existing
feedback data), the cumulative business impact the platform has "driven": total recommendations
acted on, cumulative revenue/NCF/AUM impact recorded, acceptance and completion rates, and the
trend over time. This is the slide every buyer actually remembers — but built from real recorded
data in the app, not a static graphic. Ties every technical capability back to the business
outcomes the architecture posters lead with.

### 13B.5 Verification bar
Same discipline as Section 13: the guided scenario (13B.2) must be demonstrable as one
continuous, real-data trace end to end, evidenced step by step. 13B.1's pipeline trace must show
real artifacts at every stage for a real example. Delegate the narrative/scenario design to
`fable-architect`; main thread does the wiring and UI.

## 10-RESOLUTION. Where Section 10 now sits (it has NOT executed yet — reconciled here)

Section 10 (industry-standard enhancements) was deferred and never run. After Sections 12, 13,
and 13B, much of it is either already delivered or reduced to small extensions:
- Household churn/next-best-product/concentration/review-cadence → simple extensions of Section
  11.1's model tier; build after 13B if time allows.
- AGP cohort (community detection) + mentor pairing (GNN similarity) + AGP ROI → the graph
  algorithms and embeddings now exist (Section 11); these become real, not speculative.
- Anomaly/vulnerable-client detection → already moved into Section 11.1.
- Real search/notification icons, AUM net-flows waterfall, PDF/PPT export → still valid, still
  Opus-level mechanical work.
**Sequencing: run Section 10's remaining items LAST, after 12 → 13 → 13B, and only the ones not
already satisfied by those sections — re-check each against what's actually been built before
building it, don't duplicate.** `fable-architect` only for the AGP-ROI methodology and mentor-
matching algorithm, per Section 10's own routing note; everything else Opus.

## 14. Final directive — once Sections 12, 13, 13B, and 10 are complete and verified

Switch the running configuration to **real graph mode and real LLM mode as the default** for the
client's own hands-on testing — no mock anywhere: `GRAPH_CLIENT_MODE=real` (or `local_real` if
the live TigerGraph container is the intended target) and `LLM_CLIENT_MODE=claude`. Confirm the
backend actually boots and serves correctly in this configuration before handing it over — this
is a real environment change, verify it like one, not just flip the env var and assume it works.

> **Superseded default, see Section 15.2:** the client-environment PRIMARY LLM/embedding path is
> now **cdao OpenAI** (`LLM_CLIENT_MODE=cdao_openai` / `EMBEDDING_CLIENT_MODE=cdao_openai`), not
> Claude. `LLM_CLIENT_MODE=claude` remains valid for local spot-checks; on the client machine cdao
> is PRIMARY with `azure` (SmartSDK/Fusion) as the fallback. The verify-before-handover rule above
> stands unchanged — the Connection & Environment Health screen (Section 15.7) is the gate.

## 15. Client-Environment Pre-Wiring & Production Hardening (post-Section-14) — CURRENT STATE

**Status: all of Sections 9–14 are complete and verified.** This section documents everything
built AFTER Section 14 to make the app run in the client's (JPMC) real environment and to harden
it for production hand-off. Nothing here contradicts the pipeline/data facts proven in Sections
9–13B — it changes *how the app connects to real backends* and *how durable state, logging, and
graph reasoning are made production-grade*, and adds a small set of new capabilities/pages.

**Companion docs are the field reference (read alongside this section; this section summarizes,
they carry the exact commands/values):**
- `CLIENT_SETUP_RUNBOOK.md` — literal top-to-bottom runbook for bringing the app up on the client
  machine (env → deps pre-check → install → TigerGraph → boot/health → data load → ML training →
  verify). Every command is real; gaps are flagged ⚠️.
- `CLIENT_ENV_SETUP.md` — the definitive `.env` variable reference (all adapter modes, cdao,
  SmartSDK/Fusion, TigerGraph secret, MCP tier).
- `SMARTSDK_REFERENCE.md` — confirmed-verbatim client values (TigerGraph host/user/graph, Fusion
  endpoints, SmartSDK `Model(...)` construction) — do not invent signatures, match these.
- `TIGERGRAPH_AUDIT.md` — source-of-truth audit: `docs/tigergraph_foundation/` is authoritative;
  root `tigergraph/` is legacy/reference-only.
- `DATABASES.md` — where every runtime store (two SQLite DBs, Chroma) lives and the StateRepository
  seam.
- `GRAPH_ML_AND_GDS.md` — honest inventory of what runs natively-in-TigerGraph vs. in-Python, and
  the client-machine native-GDS/GNN conversion plan.
- `ARCHITECTURE_OVERVIEW.md` / `COPILOT_CONTEXT.md` / `TROUBLESHOOTING.md` — adapter map,
  end-to-end data flow, and symptom→fix table.

Note: `MIGRATION_TO_CLIENT.md` does **not** exist — the migration content lives in
`CLIENT_SETUP_RUNBOOK.md` + `CLIENT_ENV_SETUP.md`. Do not create it as a duplicate.

### 15.1 The adapter mode matrix (the ONLY thing that changes build-box → client)

All business/prompt/query logic is identical between the build box and the client — only these
env selectors flip. Every service depends on the adapter *interface*, never an SDK (Section 2
invariant, still enforced: SDK imports live only inside their implementation class).

| Selector | Build box (here) | Client (JPMC) | Adapter module |
|----------|------------------|---------------|----------------|
| `GRAPH_CLIENT_MODE` | `mock` | `real` (or `auto`/`tiered`/`mcp` for the 4-tier cascade) | `app/graph/client.py`, `app/graph/tiered_client.py` |
| `LLM_CLIENT_MODE` | `mock` / `claude` | `cdao_openai` (PRIMARY) → `azure` (fallback) | `app/llm/client.py` |
| `EMBEDDING_CLIENT_MODE` | `local` (384-dim) | `cdao_openai` (PRIMARY, 3072-dim) → `azure` (1536) | `app/llm/embedding_client.py` |
| `MODEL_CLIENT_MODE` | `deterministic` | `real` (trained XGBoost/GNN/forecast artifacts) | `app/ml/client.py` |
| `VECTOR_CLIENT_MODE` | `local` (SQLite cosine) | `local` or `tigergraph` (native EMBEDDING/HNSW, after probe) | `app/ml/vector_client.py` |
| `STATE_STORE_MODE` | `tigergraph` (TG-authoritative + SQLite fallback) | `tigergraph` | `app/repositories/state_repository.py` |
| `LOG_SINK` | `file` | `stdout` (ECS/Fargate → CloudWatch) or `cloudwatch` | `app/shared/logging.py` |

### 15.2 cdao OpenAI adapter — the PRIMARY client LLM **and** embedding path (new)

The developer confirmed cdao works in the client's Jupyter environment — simpler than the SmartSDK
path — so it is PRIMARY for BOTH LLM and embeddings. One package (`cdaosdk-all[openai]`, pinned to
the `artifacts` uv index) and **one PCL AWS login** serve both.

- `CdaoOpenAILLMClient` (`app/llm/client.py`, `LLM_CLIENT_MODE=cdao_openai`) — wraps
  `cdao.openai_azure_client(api_version=CDAO_API_VERSION, workspace_id=CDAO_WORKSPACE_ID)` +
  `client.chat.completions.create(model=CDAO_MODEL=gpt-4o-2024-08-06, …)` behind the standard
  `LLMClient` interface. Every agent/chat/insight path consumes it via `get_llm_client().generate()`
  unchanged; verified consumed end-to-end by the LangGraph path.
- `CdaoOpenAIEmbeddingClient` (`app/llm/embedding_client.py`, `EMBEDDING_CLIENT_MODE=cdao_openai`) —
  wraps `client.embeddings.create(model=CDAO_EMBEDDING_MODEL=text-embedding-3-large-1, …)`, verified
  live returning **3072-dim** vectors. RAG ingestion + similarity consume it via
  `get_embedding_client().embed()/embed_many()` unchanged.
- **Shared construction:** both adapters build the same `openai_azure_client` via one helper
  (`build_cdao_openai_client` in `app/llm/client.py`) — one install, one login, two adapters.
- **PCL AWS login is a hard prerequisite** — cdao has NO keys in `.env`; it authenticates from the
  ambient AWS session. Run the login in the same shell that starts the backend; if it expires, cdao
  calls fail at request time (re-login + restart).
- **`EMBEDDING_DIM` is load-bearing:** `local`=384, `cdao_openai` (text-embedding-3-large-1)=**3072**,
  `azure` (text-embedding-3-small)=1536. It must match the active adapter, the Chroma collection,
  AND the TigerGraph `EMBEDDING` DDL. Switching modes requires rebuilding the Chroma collection
  (`scripts/ingest_sample_knowledge.py`). The adapter raises loudly on a mismatch — it never
  silently corrupts the vector space.
- **Env:** `CDAO_API_VERSION=2024-02-01`, `CDAO_WORKSPACE_ID=906313`, `CDAO_MODEL=gpt-4o-2024-08-06`,
  `CDAO_EMBEDDING_MODEL=text-embedding-3-large-1`, `EMBEDDING_DIM=3072`.

### 15.3 SmartSDK / Fusion — the SECONDARY (fallback) LLM + embedding path

Used only if cdao is unavailable (`LLM_CLIENT_MODE=azure` / `EMBEDDING_CLIENT_MODE=azure`).
`AzureOpenAILLMClient` / `AzureOpenAIEmbeddingClient` (`app/llm/`) build a `smart_sdk.models.Model`
(provider `AZURE_OPENAI`, key/fusion auth confirmed, certificate auth as alternate) and convert via
`_to_langgraph_model`. Endpoint `https://llm-multitenancy-exp.jpmchase.net`, workspace `906313`,
`text-embedding-3-small`=1536-dim. `smart_sdk` is intentionally NOT in `pyproject.toml` (not on
public PyPI) — install it explicitly from the client artifactory only when the azure fallback is
needed. The LangGraph→SmartSDK swap is isolated to ONE module
(`app/agents/workflows/langgraph_builder.py`) — only import paths change, signatures are identical.

### 15.4 TigerGraph MCP-first 4-tier cascade (Section 9.4, now verified)

`GRAPH_CLIENT_MODE=auto|tiered|mcp` selects `TieredGraphClient` (`app/graph/tiered_client.py`) with
automatic per-request fallback in strict order:

**Tier 1 `tigergraph-mcp` → Tier 2 `pyTigerGraph` → Tier 3 RESTPP → Tier 4 Mock.**

- Tier 1 spawns the official `tigergraph-mcp` server as a local **stdio subprocess**
  (`app/graph/tigergraph_mcp_stdio_client.py`) — no separate MCP server URL to configure; it
  receives the same `TG_*` env as the pyTigerGraph tier (one `.env`, all four tiers).
- Every dispatch is logged to a `TierUsageLog` (`app/graph/tier_log.py`): tier number/name,
  operation, latency, ok/error, and `fallback_from` naming exactly which higher tiers failed first.
  Each served result envelope carries `served_by` / `served_by_tier`. Failed tiers go on a 60s
  cooldown (`GRAPH_TIER_COOLDOWN_SECONDS`). Surfaced on the Admin/Data Health adapter-status panel.
- **Verified in codespace:** tier order, clean per-step fallback, cooldown, tier logging (natural +
  simulated fallback with real tier logs). **Not testable off the client network:** Tier 1 actually
  *succeeding* against the live TigerGraph — the live verification checklist is `CLIENT_ENV_SETUP.md`
  §3b. Auth precedence in the pyTigerGraph tier: `TG_JWT_TOKEN → TG_API_TOKEN → TG_SECRET(getToken)
  → user/pass`; with only `TG_SECRET` set, `conn.getToken(secret)` is called automatically.
- Confirmed client connection facts (`SMARTSDK_REFERENCE.md` §9): host
  `https://wh-110ecdf498.svr.us.jpmchase.net`, TigerGraph **4.2.2**, user `R757680`, graph
  `iperform_insights_coaching_demo`, `getToken(secret)` + SSL.

### 15.5 TigerGraph source of truth — `docs/tigergraph_foundation/` (audited, authoritative)

`docs/tigergraph_foundation/` is the single source of truth for schema, loading jobs, queries, and
seed data — validator-PASS and continuously extended through Sections 9–15. The repo-root
`tigergraph/` folder is the **stale 42-vertex legacy build, now explicitly marked reference-only**
(`tigergraph/README.md`); it is on NO client-rebuild path. Do not install from it.

**Current verified foundation counts (`docs/tigergraph_foundation/scripts/validate_package.py`,
STATUS PASS):**

```
vertices 60 · edges 132 (+132 reverse) · loading jobs 185 · queries 50 (GQ-001..050)
manifest files 192 · data rows 156,247   (34,070 vertex + 122,177 edge)
```

- Schema additions that back the intelligence-layer state (all validated present):
  `phx_dm_learning_weight` (GQ-044), `phx_dm_impact_ledger` + `impact_for_advisor` /
  `impact_from_recommendation` (GQ-045), `phx_dm_rec_status_transition` +
  `transition_of_recommendation` (GQ-046), `phx_dm_context_memory` by scope (GQ-047), the canonical
  `phx_dm_reasoning_trace` + `phx_dm_reasoning_for_advisor` + traversal queries (GQ-048/049/050),
  and `phx_dm_guardrail_event`.
- `impact_ledger` and `reasoning_for_advisor` are **intentionally header-only / runtime-accumulated**
  (seeding them would make `replay_on_boot` inject revenue at boot and silently mutate anchored
  advisor figures — Section 14 decision, still correct). A rebuild from the foundation alone
  reproduces the complete current graph, these types intentionally starting empty.
- The real gate is `docs/tigergraph_foundation/scripts/validate_package.py` — NOT the repo-root
  `scripts/validate_tigergraph_foundation.py` (that one validates the *legacy* package; documented
  naming trap, not renamed to avoid breaking references).
- **Schema teardown/rebuild:** `docs/tigergraph_foundation/tigergraph/schema/99_drop_all.gsql`
  drops, in TigerGraph-correct order, the graph → **133** forward edge types (reverse edges
  auto-drop with their forward edge) → **60** vertex types at `USE GLOBAL`. Object lists were
  derived programmatically from `01_vertices.gsql`/`02_edges.gsql` (not hand-typed). Structurally
  validated; execute live on the client machine to fully confirm.
- **Edge count 132 vs 133 — reconciled, not a contradiction:** the validator/loaded/manifest count
  is **132** edges (what `validate_package.py` reports and what the 156,247-row load covers). The
  `99_drop_all.gsql` header says **133** forward edges because it drops from the live
  `01_vertices.gsql`/`02_edges.gsql`, which include one edge (`phx_dm_transaction_from_recommendation`,
  added in Section 13) not yet reflected in the slightly-stale `schema_catalog.json` the validator
  reads. Both numbers are correct for what they describe; the graph runs on 132.

### 15.6 Data Ingestion "Run All" — full graph load (Section 3B page, completed)

The **Data Ingestion & Sync** page loads the COMPLETE graph, not a partial subset. Registry is
generated from the manifest (**192 entities = 60 vertices + 132 edges**), with edge-aware bulk
ingestion and a "Run All Ingestion" control showing per-entity progress. Endpoints:
`POST /ingestion/run-all` (background worker, manifest order, batch size 500) and
`GET /ingestion/run-all/status` (per-entity counts + mismatches). Loads the 192 manifest CSVs from
`docs/tigergraph_foundation/data/sample/{vertices,edges}/` via real RESTPP upserts. Alternative:
server-side GSQL loading jobs (`.../loading/run_all_loading_jobs.sh`). The earlier "Capabilities
Locked" section was removed.

### 15.7 Connection & Environment Health screen (new — the setup gate)

A real active-verification page (`GET /env-health`, plus `GET /graph-access/health` for the tiered
adapter). It actively checks — each green/red with the real error if red:
- **TigerGraph** — reachable, auth/SSL, graph present, schema installed, per-vertex-type row counts.
- **LLM** — a real test generation (latency + response) via the active adapter (cdao/azure).
- **Embedding** — a real embed + the configured `EMBEDDING_DIM`.
- **Chroma** — reachable + collection count.

`overall: green` is the gate — do not load data or train models until it is green. Verified in
codespace under mock modes (`overall: green`; OpenAPI exposes **146** routes). Live greens (cdao,
real TigerGraph) verify on the client machine.

### 15.8 StateRepository — durable state made TigerGraph-authoritative (new seam)

Per `DATABASES.md`, all durable runtime state (memory, learning/bandit weights, impact ledger,
recommendation status) was previously hardcoded to SQLite with no adapter seam. `app/repositories/
state_repository.py` introduces the seam, following the GraphClient/LLMClient pattern:

```
STATE_STORE_MODE=tigergraph (default) → TigerGraphStateRepository PRIMARY, SQLite FALLBACK
STATE_STORE_MODE=sqlite               → SqliteStateRepository only (legacy behavior)
```

Three concrete implementations: `TigerGraphStateRepository` (PRIMARY — writes state as graph
vertices/edges via the existing `GraphClient`, reads it back by traversal: installed GQ queries in
real mode, mock equivalents in mock mode), `SqliteStateRepository` (retains the exact prior SQLite
logic), and `FallbackStateRepository` (graph-authority-then-auto-SQLite, logged, never crashing —
the safety net for the client env's first run). Access everything via `get_state_repository()`;
the previously-empty `BaseRepository` stub is now filled.

**All four durable-state domains are migrated onto the seam** (Sessions 13–14): the six memory
types (`phx_dm_context_memory` by scope, GQ-047, with Procedural now populated organically),
learning/bandit weights (`phx_dm_learning_weight`, GQ-044), the impact ledger (`phx_dm_impact_ledger`
+ edges, GQ-045), and recommendation status + transitions (`phx_dm_rec_status_transition` +
`transition_of_recommendation`, GQ-046). Direct `sqlite3`/`SQLiteManager()` calls were removed from
these durable-state call sites; only the generated-recommendation attribute *cache* remains SQLite
(a documented operational cache, not authoritative state). This makes TigerGraph the intended
"memory and intelligence backbone" the Temporal Knowledge Graph architecture calls for, while local
dev keeps SQLite as the fast fallback. (The `state_repository.py` module docstring still describes
feedback/impact/status as "being migrated" — that comment is stale; the migration landed per
`PROGRESS.md` Session 14, commits `0b11e92`/`5c58dd5`/`1dad658`.)

Two gitignored SQLite DBs remain (both auto-recreate on an empty clone via `CREATE TABLE IF NOT
EXISTS` + reseed scripts): `data/feature_store/iperform_features.db` (active runtime writes,
feature vectors, GNN/FL/model outputs, ingestion checkpoints) and `data/sqlite/iperform.db`
(preloaded demo snapshot). Chroma at `data/chroma/` holds document/RAG vectors only.

### 15.9 Guardrail layer — real input/output AI protections (new)

`app/guardrails/` (`client.py` / `service.py` / `models.py`, `GuardrailClient` adapter:
local regex/heuristic default | SmartSDK `EvaluationService`) is wired on the live AI path — both
chat and agentic:
- **INPUT:** PII redaction, prompt-injection / jailbreak detection (BLOCK).
- **OUTPUT:** PII filter, toxicity, grounding / hallucination check (answers must trace to retrieved
  evidence).
Events persist to `phx_dm_guardrail_event` (10 seeded rows load). Verify guardrail *behavior* with
`LLM_CLIENT_MODE=claude` (real calls), never mock.

### 15.10 Graph relational reasoning — consolidated + wired (extends 11.6b)

The reasoning-trace representation is now **one canonical vertex** `phx_dm_reasoning_trace` (PK
`reasoning_id`; attrs `artifact_type/artifact_id/reasoning_steps_json/evidence_json/model_name/
prompt_version/confidence/created_at`), used by BOTH the Explainability/Memory-Timeline display path
and the reasoning-reuse path — resolving an earlier accidental divergence where the memory-service
write path emitted a different vertex shape + a dead edge (fixed in commit `a226193`; do not
re-introduce a second shape). For every AI answer the context assembler performs genuine multi-hop
graph traversal (`app/ai/reasoning/graph_reasoner.py`, GQ-048/049/050): advisor → households →
opportunities/outcomes → `phx_dm_advisor_has_similarity_match` → similar advisors → their proven
action families; and prior traces for that advisor are retrieved by traversal and fed back in
(experience memory). **Traversal is real and instrumented (actual entities visited are returned),
never LLM-narrated.** Surfaced via `/explainability/graph-reasoning/{scope}/{id}` + the
`GraphReasoningPath` UI panel.

### 15.11 Agent Orchestration — real-vs-static audit + live agent graph (new)

The Agent Orchestration page was audited (two-run evidence) and rewired from static sections to real
per-run data: a **live agent system graph**, real per-agent decisions, real guardrail + compliance
sections, and per-run confidence (previously hardcoded). Five defects found and fixed during the
audit (fake-in-effect graph evidence, broken opportunity render, hardcoded confidence, hidden
adapter tier, RAG corpus 10× duplicated). The "Run Workflow" button runs the real orchestration
path (`/orchestration/run`).

### 15.12 Revenue Trend Explorer — now its own dedicated page (Section 9.6, promoted)

Moved from being folded into Revenue Analytics to its own page
(`frontend/app/(dashboard)/revenue-trend-explorer`). Bar chart of revenue over a user-selected
date range + granularity (monthly/quarterly), sliced by advisor/region/market/division/branch, with
exact-figure driver bullets per period, an up/down indicator vs. the prior comparable period, and a
real Claude-generated headline summary grounded in the underlying data (same evidence standard as
every AI-generated card). Full month/quarter breakdown across the expanded date range.

### 15.13 Graph ML / GDS — the honest current reality (see `GRAPH_ML_AND_GDS.md`)

Be precise about WHERE compute happens — results are real either way:
- **Runs natively IN TigerGraph today:** entity/relationship storage (the 60v/132e/156,247-row
  temporal knowledge graph) and real multi-hop GSQL traversal reasoning (the backbone of the
  agentic graph-reasoning feature).
- **Runs in PYTHON today (TigerGraph as data source, not compute engine):** classical graph
  algorithms — PageRank (referral-network centrality) and Louvain (AGP cohort/community detection)
  via **networkx** (`app/ml/graph_algorithms.py`), NOT native GDS; the **GraphSAGE GNN** via **local
  PyTorch Geometric** (`app/ml/gnn.py`, `scripts/train/train_graphsage_embeddings.py`), NOT
  `pyTigerGraph[gds]`'s `neighborLoader`; plus XGBoost/RandomForest + SHAP, a GRU revenue forecast,
  and Isolation Forest anomaly detection — all standard Python ML with deterministic fallbacks.
- **Native conversion is a documented CLIENT-ENVIRONMENT task**, not a codespace gap: `GRAPH_ML_AND_
  GDS.md` Part 2 gives the step-by-step (install native GDS library; repoint algorithms networkx→GDS;
  `ALTER VERTEX … ADD EMBEDDING (DIMENSION=3072, INDEX=HNSW, METRIC=COSINE)`; native GraphSAGE via
  `neighborLoader`). It needs a live TigerGraph 4.2.2 instance (unreachable from the build box) and
  the `pyTigerGraph[gds]` extra — which is **commented out / optional in `pyproject.toml` and used by
  nothing yet** (anticipatory only). Every native step keeps its Python fallback. There are NO
  `ADD EMBEDDING`/HNSW/`Featurizer`/PageRank/Louvain `.gsql` install scripts in the repo — the honest
  claim is "TigerGraph stores the graph and does real multi-hop traversal reasoning; the GNN/ML runs
  in Python today, with a documented path to native GDS/GNN on the client's instance."

### 15.14 pyproject alignment + dependency pre-check tooling (new)

- `pyproject.toml` aligned to the client reference: client deps merged (`cdao*` guarded optional
  under `[cdao]`), both uv indexes + `[tool.uv.sources]` + google-adk metadata, floors replaced for
  `fastapi`/`uvicorn`. Verified: backend imports + frontend build both succeed. `[tool.uv] package =
  false` — the intended flow is `uv venv` + `uv pip install -e .` (there is no `uv.lock`; the
  committed lockfile is `poetry.lock`). `uv.toml` (committed) points every dependency, including
  client-only `smart_sdk`/`cdao*`, at the artifactory.
- **Dependency pre-check (run BEFORE any install):** `scripts/check_client_deps.py` (every pyproject
  group + `smart_sdk`) and `scripts/check_client_npm.py` (frontend deps). Each reports
  AVAILABLE/VERSION-MISMATCH/MISSING against the client artifactory; exit 0=pass, 1=required-dep
  issue, 2=index unreachable. The four client-only packages (`smart_sdk`, `cdaosmart-sdk`,
  `cdaosdk-all`, `cdaosmart-evals`) correctly show MISSING on public PyPI. `frontend/.npmrc.client-
  template` (committed, no token) activates the client npm registry.

### 15.15 Structured logging — CloudWatch-ready (new)

`app/shared/logging.py` configures stdlib `logging` to emit structured JSON identically on a laptop
and on ECS/Fargate. Every record carries ISO-8601 UTC timestamp, level, logger name,
correlation/request id (`app/shared/correlation.py`), message, and full exception+stack on errors.
Sink is config, not code — `LOG_SINK=file` (local default, rotating `logs/app.log`) | `stdout`
(recommended for Fargate → CloudWatch via the awslogs driver, no in-app AWS SDK needed) |
`cloudwatch` (direct `watchtower` push, falls back to stdout if the package/creds are missing so the
app never fails to boot over logging). `LOG_JSON=true` by default; `LOG_JSON=false` for a coloured
console during local debug.

### 15.16 Setup runbook + launchers + UX polish (new)

- **Launchers:** `scripts/run_all.sh` (combined backend :8000 + frontend :3000; uses `uv run` when
  present, falls back to `python -m uvicorn`; `API_PORT`/`UI_PORT`/`API_HOST` overrides — verified
  backend HTTP 200 / frontend HTTP 307). `scripts/train/run_all.sh` — full ML/GNN training
  orchestrator over all 7 trainers (revenue-decline, household churn, AGP off-track, revenue
  forecast, GraphSAGE, anomaly, FL fine-tune) with `PYTHONPATH=.` set, per-step time-box
  (`ML_TIME_BOX_MINUTES`, default 10), and skip-on-missing-dep. Artifacts → `models/artifacts/`,
  registry → `models/registry.json`. (The older `run_all.py` covered only the 3 tabular classifiers;
  it was left untouched.)
- **UX polish:** shared loading/spinner + error states for async/AI content; larger multi-line
  question textarea on the workflow runner and AI Assistant; explicit spinner + label on the Revenue
  Trend Explorer load. Browser-access fix: bind `0.0.0.0`, ports 3000/8000 set Public, `NEXT_PUBLIC_
  API_BASE_URL` = the public forwarded URL for browser fetches vs. `API_BASE_URL_INTERNAL` =
  loopback for SSR/tooling — verified through the real public browser path.

### 15.17 Anchored figures — PRESERVED (do not let these drift)

The build's credibility rests on these verified anchors; every model trainer asserts them:
- **A001 `revenue_ltm` = $387,293.22** (anchor check in `scripts/train/train_revenue_decline.py`
  prints `anchor check OK — A001 revenue_ltm=387293.22`; `test roc_auc = 0.7755`, floor 0.65 → PASS).
- **A001 MANAGED_MIX = 1.08**, **144** revenue-neutral status-transition vertices reproduce from CSV
  alone (Section 14 graph-from-CSV verification).
- Recommendation-completion propagation **+$47,053.23** verified visible at advisor / market /
  division scopes (Section 13B cross-screen propagation).
Any expansion must ADD entities/date-range/variety only — never regenerate or mutate an anchored
advisor's figures. If a genuine reason ever requires changing one, state exactly what changed and
why, prominently, in `PROGRESS.md`.

### 15.18 Client hand-off configuration (Section 14, restated with the current PRIMARY modes)

No mock anywhere, verified booting before hand-off:
`GRAPH_CLIENT_MODE=real` (or `auto` for the tiered cascade / `local_real` for a local Docker TG),
`LLM_CLIENT_MODE=cdao_openai` (PRIMARY; `claude` for spot-checks; `azure` fallback),
`EMBEDDING_CLIENT_MODE=cdao_openai` (`EMBEDDING_DIM=3072`), `MODEL_CLIENT_MODE=real`,
`STATE_STORE_MODE=tigergraph`, `LOG_SINK=stdout`. PCL AWS login first (cdao); then the Connection &
Environment Health screen must be all-green before demoing. Follow `CLIENT_SETUP_RUNBOOK.md`
top-to-bottom — it is the authoritative sequence.