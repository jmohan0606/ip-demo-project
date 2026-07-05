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
