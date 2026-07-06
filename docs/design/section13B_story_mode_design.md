# Section 13B Design — Guided End-to-End Story Mode

Author: fable-architect (Section 13B delegation). Date: 2026-07-06.
Status: APPROVED DESIGN — implementable as-written by the main (Opus) thread.

Every path, endpoint, and field below was verified against the actual codebase before being
referenced (files read: `docs/design/section13_lifecycle_design.md`, `frontend/lib/navigation.ts`,
`frontend/components/layout/app-shell.tsx`, `shell-context.tsx`,
`frontend/components/explainability/explainability-workspace.tsx`, `context-pipeline-panel.tsx`,
`frontend/lib/hooks/use-scoped-advisor.ts`, `frontend/app/(dashboard)/layout.tsx`,
`frontend/components/recommendations/recommendations-workspace.tsx` (learning-state imports),
`app/api/routers/{explainability,observability,impact_ledger,feedback_learning,predictions,
insights_coaching,advisor360,revenue,scope,ai_chat,coaching}.py`, `app/observability/recorder.py`,
`app/recommendations/{service,compliance_validator,lifecycle}.py` (grep-level),
`app/scope/{dashboard,rollup}.py` (grep-level), `scripts/verify_section13_lifecycle.py`).

---

## 0. Ground truth this design is built on (verified facts, not assumptions)

1. **Section 13 is real and complete.** Lifecycle state machine, impact ledger, exact-to-the-cent
   propagation on 3 screens, addressed-opportunity regeneration, AI-context plumbing — all
   verified (`scripts/verify_section13_lifecycle.py`, 9 assertion groups PASSED). 13B adds NO new
   state; it narrates this.
2. **Current pristine state (from PROGRESS.md §13 closure):** A005 base `revenue_ltm = 406375.14`,
   impact ledger EMPTY, A001 anchored at 387293.22. The guided scenario is what populates the
   ledger live — by design.
3. **`record_stage`/`stage_timer` exist in `app/observability/recorder.py` but have ZERO callers
   today** (verified by grep: only the recorder module and the `/observability/stage-spans`
   router reference them). `GET /observability/stage-spans` currently returns an empty list.
   13B.1 is therefore the FIRST real producer of stage spans — the recorder infrastructure is
   ready, the instrumentation is the missing piece. State this honestly; do not claim timing
   already exists.
4. **Compliance is NOT on the live recommendation path.** `RecommendationComplianceValidator`
   (`app/recommendations/compliance_validator.py`) is real, deterministic (blocked-terms,
   evidence-presence, suitability-language checks → PASSED / NEEDS_REVIEW / BLOCKED + warnings)
   but is only used by the dormant `recommendation_engine.py` path. The live
   `RecommendationService.generate_for_advisor` payload has no compliance field (verified by
   grep). 13B.1's "Context & Compliance" stage requires a small additive change (§1.3).
5. **The explainability chain endpoint already returns 9 artifact arrays**:
   `GET /explainability/recommendation/{rec_id}` → `{recommendation, opportunities, predictions,
   features, playbooks, reasoning, feedback, outcomes, learning}` (vertex lists). The reasoning
   vertex carries `reasoning_steps_json` + `evidence_json`. `REASON_{rec_id}` is written at
   generation time (`app/recommendations/service.py` lines 316/374).
6. **The shell is the right mount point for an overlay.** `AppShell`
   (`frontend/components/layout/app-shell.tsx`) provides `ShellContext` with `setScope`,
   `setPersona`, `setPeriod`, `refresh`, `refreshNonce` and wraps every dashboard route
   (`frontend/app/(dashboard)/layout.tsx` is just `<AppShell>{children}</AppShell>`). A provider
   mounted inside AppShell persists across `router.push` navigations and can drive scope changes
   — exactly what a guided walkthrough needs.
7. **`useScopedAdvisor`** resolves any rollup scope to its first advisor; setting shell scope to
   `("Advisor", "A005", label)` makes Predictions / Recommendations / Explainability / Feature Lab
   / AI Assistant all follow (Section 9.1/12.6, verified).
8. **Replay/reset mechanics exist but are restart-dependent today**: `verify_section13_lifecycle.py
   --reset` deletes the advisor's rows from `phx_dm_local_recommendation`,
   `phx_dm_local_rec_status_transition`, `phx_dm_local_impact_ledger`, and lifecycle memories,
   then recomputes the snapshot — but its own comment notes the injected in-memory `TXIMP_`
   transaction survives until backend restart. True same-process replayability needs a runtime
   vertex/edge removal helper (§2.5). This is the one genuinely new mechanism 13B adds, and it
   touches only `TXIMP_`-prefixed runtime vertices — never seed data.
9. **Endpoints available for every scenario step** (all verified in routers):
   `POST /predictions/run/{id}`, `GET /predictions/revenue-decline/{id}`,
   `GET /predictions/forecast/{id}`, `GET /advisor/360/{id}`, `GET /advisor/360/{id}/ai`,
   `POST /recommendations/generate/{id}`, `POST /feedback-learning/submit`,
   `POST /recommendations/{id}/transition`, `GET /recommendations/{id}/lifecycle`,
   `GET /impact-ledger[/advisor/{id}]`, `GET /revenue/analytics?scope_type&scope_id&period`,
   `GET /scope/summary|dashboard|ai-insight?scope_type&scope_id`, `GET /feedback-learning/state`,
   `GET /feedback-learning/impact-trend`, `GET /feedback-learning/outcome-learning`,
   `POST /ai-chat/ask`, `GET /ai-chat/context-trace`, coaching CRUD
   (`GET /coaching/task-catalog`, `POST /coaching/tasks`, `PATCH /coaching/tasks/{id}/status`).
10. **The Recommendations workspace already renders** server-driven lifecycle (status badge,
    terminal disable, Start button, `lifecycle_counts`, impact note, Addressed section,
    `LearningStateShowcase`, `OutcomeLearningPanel`) — the overlay highlights these, it does not
    rebuild them.
11. **Nav groups**: `["Executive", "Advisor", "AI", "Graph", "Operations", "Admin"]`. Existing AI
    group already contains `/recommendations`, `/impact-ledger`, `/recommendation-roi`.
12. **`GET /impact-ledger` totals shape**: `{total_impact, completed_count, advisors_affected,
    by_family, by_advisor}` — 13B.4 extends totals additively (§4.2), it does not change existing keys.

---

## 1. 13B.1 — "How It Works" pipeline trace (extends Explainability Explorer; NOT a new page)

### 1.1 One new compose endpoint (justified — 6 stages come from 5 different sources, and
per-stage timing must be measured server-side)

`GET /explainability/pipeline-trace/{recommendation_id}` (add to
`app/api/routers/explainability.py`; implementation in a new
`app/services/pipeline_trace_service.py` or directly beside the explainability query helpers —
implementer's choice, keep it one module).

It stitches existing sources; each stage's assembly is wrapped in
`recorder.stage_timer(name, sink)` and the whole request finishes with
`recorder.record_stage(f"pipeline-trace {rec_id}", stages)` — making this the first real
producer for `GET /observability/stage-spans` (fact 0.3) and lighting up the Admin
Observability tab's stage-span table with real rows as a side effect.

Response shape:

```json
{
  "recommendation_id": "REC_OPP_MANAGEDMIX_A005_v2.0",
  "advisor_id": "A005",
  "total_ms": 412.6,
  "timing_basis": "generation",            // "generation" | "assembly" — see §1.2
  "stages": [
    {"key": "data",           "label": "Data",                      "ms": 38.2,
     "summary": "Advisor A005 · 214 transactions · 18 households · graph facts",
     "artifact": {"advisor_id": "A005", "advisor_name": "…",
                  "entity_counts": {"transactions": 214, "households": 18, "accounts": 41},
                  "snapshot_id": "SNAP_…", "as_of": "2026-07-03"}},
    {"key": "features",       "label": "Feature Engineering",       "ms": 61.0,
     "summary": "33-feature snapshot · revenue_ltm $406,375 · lineage attached",
     "artifact": {"snapshot_id": "…", "top_features": [{"name": "revenue_ltm", "value": 406375.14,
                  "lineage": "GQ-004 over transactions"}, "… 5-8 client-legible features …"]}},
    {"key": "model",          "label": "Model",                     "ms": 143.1,
     "summary": "REVENUE_DECLINE_RISK · 61/100 · confidence 0.78 · RandomForest (real-label)",
     "artifact": {"prediction_id": "…", "prediction_type": "…", "score": 61, "confidence": 0.78,
                  "model": "… from the prediction vertex / model registry …",
                  "contributions": [{"feature": "…", "value": …, "direction": "…"}]}},
    {"key": "derivation",     "label": "Opportunity → Recommendation", "ms": 84.3,
     "summary": "MANAGED_MIX opportunity (sev attention) → 'Run managed-account review sprints' · est. +$52,111",
     "artifact": {"opportunity": {"opportunity_id": "…", "category": "…", "severity": "…", "score": …},
                  "recommendation": {"title": "…", "priority_score": …, "base_priority_score": …,
                  "learning_weight": …, "estimated_revenue_impact": …}}},
    {"key": "context_compliance", "label": "Context & Compliance",  "ms": 52.7,
     "summary": "2 playbooks retrieved · 7 evidence facts · compliance PASSED",
     "artifact": {"playbooks": [{"id": "…", "title": "…"}], "evidence": {"…": "…"},
                  "reasoning_steps": ["…"],
                  "compliance": {"status": "PASSED", "warnings": []}}},
    {"key": "output",         "label": "Delivered Output",          "ms": 33.3,
     "summary": "COMPLETED · +$52,111 recorded (TXIMP_…)  — or —  OPEN · awaiting action",
     "artifact": {"status": "…", "status_note": "…", "allowed_actions": [], "terminal": true,
                  "impact": {"…": "…"},
                  "transitions": [{"from": "OPEN", "to": "ACCEPTED", "ts": "…", "actor": "…"}]}}
  ]
}
```

Stage → real source mapping (all reuse, no new computation invented):

| Stage | Fed by | Notes |
|---|---|---|
| Data | the explainability chain's `features` vertex + `FoundationGraphStore` counts (`advisor_transactions`, household/account out-edges) | same store reads Advisor 360 uses |
| Feature Engineering | `SnapshotStore.latest_for_entity("ADVISOR", id)` — real values + lineage fields | pick 5-8 client-legible features (revenue_ltm, aum_total, meetings, pipeline), not all 33 |
| Model | chain `predictions[0]` attributes (type, score, confidence, contributions JSON); model name/version resolved from the model registry where the prediction carries it | real SHAP contributions from §11.1 where present |
| Opportunity → Recommendation | chain `opportunities[0]` + `recommendation[0]` attributes, incl. `base_priority_score × learning_weight = priority_score` (already in the payload — fact 0.10) | shows the bandit visibly inside the trace |
| Context & Compliance | chain `playbooks` + `reasoning[0]`'s `evidence_json`/`reasoning_steps_json` + a LIVE run of `RecommendationComplianceValidator.validate(action_text, rationale, evidence)` | the validator is real and deterministic (fact 0.4) — running it at trace time is a real check, not a stored claim |
| Delivered Output | `RecommendationLifecycleService.lifecycle_for(rec_id)` — status, note, transitions, impact | the §13 audit trail, verbatim |

### 1.2 Timing: real, with an honest two-tier basis

- **Generation timing (preferred)**: instrument `RecommendationService.generate_for_advisor`
  itself with 4 `stage_timer`s — feature-snapshot read, prediction read/scoring, opportunity
  detection, recommendation mapping+persist — and `record_stage(f"recommendation-pipeline
  {advisor_id}", stages)`. The compose endpoint looks up the most recent matching span from
  `recorder.stage_spans()` and, when found, reports it with `timing_basis: "generation"` —
  genuinely the time the real pipeline took to produce this batch.
- **Assembly timing (fallback)**: when no generation span exists in the ring buffer (process
  restarted since generation), the endpoint reports its own measured per-stage assembly times
  with `timing_basis: "assembly"` and the UI labels the bar "trace assembly timing" instead of
  "pipeline execution timing". Never fabricate a generation time that wasn't measured.

### 1.3 One small additive backend change: compliance on the live rec payload

In `generate_for_advisor`'s mapping loop, run
`RecommendationComplianceValidator().validate(action_text, rationale, evidence_list)` per rec and
add `"compliance": {"status": "PASSED|NEEDS_REVIEW|BLOCKED", "warnings": [...]}` to the rec dict
(and mirror `compliance_status` into the SQLite row — the column already exists in
`phx_dm_local_recommendation`, fact: `lifecycle.py` line 66). Cost: microseconds (string checks).
This gives the Recommendations page a real compliance chip (scenario step 5 highlights it) and
the trace's stage 5 a persisted verdict consistent with the live check. This is the ONLY
generation-payload change 13B makes; everything else is read-only composition.

### 1.4 UI — `PipelineTraceBar`, inserted into the existing Explainability Explorer

New component `frontend/components/explainability/pipeline-trace-bar.tsx`, rendered in
`explainability-workspace.tsx` directly ABOVE the existing "Lineage chain" card (which stays —
the lineage chain is the artifact-graph view; the trace bar is the narrative/timing view; they
answer different questions and share the selected `recommendation_id`):

- Horizontal row of 6 stage cards (design-system tokens, AI-accent border like the existing
  chain nodes), each: label (11px uppercase), one-line `summary`, and the stage `ms`.
- Beneath: the SYSTEM TRACE bar (Hackathon-mockup visual) — one flex row, segment widths
  proportional to `ms`, each segment labeled `{label} {ms}ms`, total at the right, plus a small
  `timing_basis` chip ("pipeline execution" vs "trace assembly", honest per §1.2).
- Clicking a stage card expands a detail drawer below the bar rendering that stage's `artifact`
  (features table with real values, contribution bars, compliance verdict + warnings,
  transitions timeline) — reusing existing pattern components (`EvidenceTracePills`,
  severity badges, currency util).
- Add `data-story-target="pipeline-trace"` to the container (used by 13B.2's highlighter).

Since it works for ANY recommendation-backed AI output, the Recommendations workspace's inline
explainability panel gets a "How was this produced? →" link that deep-links to
`/memory-explainability` with `?rec={id}` (the workspace already selects a rec via its rec-id
chip row — add support for reading the query param to preselect). Insights/predictions reuse:
the trace endpoint is keyed by recommendation_id because that is where the full 6-stage chain
converges (predictions and insights appear as stages 3 and 5 of the same story) — do NOT build
per-artifact-type variants in 13B; that generalization is future work, stated honestly.

---

## 2. 13B.2 — Guided scenario walkthrough (the ONE genuinely new overlay surface)

### 2.1 Architecture

Three pieces, all frontend except one small reset endpoint:

1. **`StoryModeProvider`** — `frontend/components/story/story-mode-provider.tsx`. Mounted INSIDE
   `AppShell` (between `ShellContext.Provider` and the layout div) so it can call
   `useShellContext()` and `useRouter()` and never unmounts across navigation (fact 0.6). Holds:
   active scenario id, step index, scenario advisor id, `baselines` (captured at start),
   `captured` (values recorded from real action responses), status per step. Persists this state
   to `sessionStorage["iperform-story-state"]` on every change and restores on mount — this is
   what makes the overlay survive the route changes it itself triggers.
2. **`StoryOverlay`** — `frontend/components/story/story-overlay.tsx`, rendered by the provider
   above `<main>`: a bottom-docked card (fixed, full-width, ~180px, dark-navy surface matching
   the sidebar tokens, so page content stays visible above it). Contents: scenario title +
   "Step {n}/{N}" progress dots, step title, 2-3 sentence narration, a "LOOK AT" line naming the
   highlighted element, a real-value **proof chip** (green when the fetched value satisfies the
   step's check — e.g. "ledger impact $52,110.55 == estimated impact ✓"), and controls:
   Back / Next (or the step's action button, e.g. "Accept & Complete — real API call") / Exit.
3. **Highlighting** — steps carry a `highlight` key matching a `data-story-target="…"` attribute.
   The provider, after `router.push` resolves and the target appears (poll
   `document.querySelector` with a ~5s timeout — pages fetch real data, so allow for it), adds a
   CSS class (`story-highlight`: 2px AI-accent ring + soft pulse via existing Framer/CSS tokens,
   restrained) and `scrollIntoView`s it. Add `data-story-target` attributes to ~10 existing
   components (listed per step in §2.4) — attribute-only edits, zero behavior change.

Declarative step script — `frontend/components/story/scenarios.ts`:

```ts
export interface StoryStep {
  id: string;
  title: string;
  narration: string;                 // non-technical, 2-3 sentences
  lookAt: string;                    // "LOOK AT: …" line
  route: string;                     // router.push target
  scope?: { type: ScopeType; id: string; label: string };  // shell.setScope before navigating
  highlight?: string;                // data-story-target value
  action?: {                         // a REAL backend call the overlay drives (Next becomes this button)
    label: string;                   // e.g. "Accept & Complete (real state machine)"
    calls: Array<{ method: "GET" | "POST"; path: string; body?: object }>;
    captureAs?: string;              // store response under captured[captureAs]
  };
  proof?: {                          // the real value that proves the step, rendered as the proof chip
    fetch: { path: string };
    extract: (data: unknown, ctx: StoryContext) => { label: string; pass: boolean };
  };
}
```

Scenario advisor is a parameter of the scenario context (default **A005** — non-anchored, §13's
verified subject with a clean base of 406375.14; A001/A020 refused, see §2.5). Steps reference
it via `{advisor}` templating resolved at runtime, so the scenario runs for any advisor a
presenter picks — with the launch page stating plainly that completing a recommendation
**really mutates that advisor's data** (additively, ledger-recorded — the §13 guardrail language).

### 2.2 Route + nav entry

- Route `frontend/app/(dashboard)/story/page.tsx` → `frontend/components/story/story-launch.tsx`:
  scenario cards ("Advisor Journey — Detect → Act → Measure → Learn", "Division Leader Journey" §3),
  an advisor selector (default A005, `GET /advisor/360/list`), a plain-language "what will happen
  / what really changes" panel, a "Reset scenario advisor first" toggle (default ON, §2.5), and
  Start. Start captures baselines (§2.3), optionally resets, then begins step 1.
- Nav entry (`frontend/lib/navigation.ts`, group `"AI"`, FIRST in the group — it is the front
  door to everything else in that group):
  `{id: "story-mode", label: "Guided Story Mode", description: "One real end-to-end journey:
  detect a risk, explain it, act on it, and watch the measured impact propagate and the system
  learn.", href: "/story", iconName: "PlayCircle", group: "AI", status: "new"}`.

### 2.3 Baselines captured at scenario start (what makes step 8's before/after real)

On Start, the provider fetches and stores (all existing endpoints):
- `GET /revenue/analytics?scope_type=ADVISOR&scope_id={advisor}&period=ALL` → `kpis.total_revenue`
- `GET /advisor/360/{advisor}` → `feature_snapshot.features.revenue_ltm`
- `GET /scope/summary?scope_type=FIRM&scope_id=F001` → `totals.revenue_ltm`
- `GET /feedback-learning/state` → the per-family weights
These are the exact four figures §13's verification proved move by exactly the impact; the
overlay re-fetches each at the propagation/learning steps and renders `before → after (+Δ)` with
a green check when `Δ == captured.impactAmount` (to the cent — same assertion the §13 script makes,
now performed live in front of the client).

### 2.4 The 10 steps, concretely (Advisor Journey; advisor = `{A}`)

| # | Title / spec step | Route + scope | Highlight (`data-story-target`) | Real action / proof |
|---|---|---|---|---|
| 1 | **Trigger — a risk is detected** | `/predictions`, scope Advisor {A} | `prediction-revenue-decline` (revenue-decline card in the predictions workspace) | proof: `GET /predictions/revenue-decline/{A}` → "risk score {score}/100, confidence {c}" (real model output) |
| 2 | **Diagnosis — the AI explains why** | `/advisor-360`, scope Advisor {A} | `ai-insight-card` (the AI Insight Summary card) | proof: `GET /advisor/360/{A}/ai` → insight present; narration points at the named real drivers |
| 3 | **Prediction & risk — how the score was derived** | `/predictions` | `prediction-contributions` (contribution bars / methodology detail) | proof: contributions array non-empty; narration: "each bar is a real feature's measured contribution" |
| 4 | **Opportunity & recommendation** | `/recommendations` (page itself calls `POST /recommendations/generate/{A}`) | `rec-card-top` (top recommendation card) + link to the §1.4 trace | proof: top rec's `estimated_revenue_impact` → stored as `captured.impactEstimate`; `captured.recId`, `captured.family` |
| 5 | **Compliance — checked before it reaches you** | `/recommendations` | `rec-compliance-chip` (new chip from §1.3) | proof: `compliance.status` (PASSED/NEEDS_REVIEW with its real warnings listed) |
| 6 | **Action — accept and complete (real state machine)** | `/recommendations` | `rec-card-top` action row | ACTION button: `POST /feedback-learning/submit {recommendation_id, action: "ACCEPT", …}` then `{action: "COMPLETE"}` (actor_id `story-mode`); captures `lifecycle.status_note`, `impact.impact_amount`, `TXIMP_` id; then `shell.refresh()` → the card visibly flips to COMPLETED with disabled buttons (the §13 UI, live) |
| 7 | **Impact — a real consequence was recorded** | `/impact-ledger` | `ledger-table` | proof: `GET /impact-ledger/advisor/{A}` → entry with `impact_amount == captured.impactEstimate` ✓, tx id shown |
| 8a | **Propagation — Revenue Analytics moved** | `/revenue-analytics`, scope Advisor {A} | `revenue-kpi-total` | proof: re-fetch analytics → `total_revenue == baseline + impact` (to the cent, green check) |
| 8b | **Propagation — Advisor 360 moved** | `/advisor-360` | `advisor-kpi-revenue` | proof: `revenue_ltm == baseline + impact` |
| 8c | **Propagation — the firm rollup moved** | `/dashboard`, scope Firm F001 | `exec-kpi-revenue` | proof: firm `totals.revenue_ltm == baseline + impact` |
| 9 | **Learning — the system got smarter** | `/recommendations` (LearningStateShowcase section) | `learning-state` | proof: `GET /feedback-learning/state` → `{family}` weight before → after (from baseline), e.g. "1.39 → 1.44 — future {family} recommendations rank higher" |
| 10 | **Closure — ask the AI about it** | `/ai-assistant`, scope Advisor {A} | `chat-input` | overlay pre-fills "What has this advisor recently completed and what was the measured impact?"; user sends (REAL Claude when `ANTHROPIC_API_KEY` present — overlay shows an honest amber note when `LLM_CLIENT_MODE` is mock); proof: answer text references the rec title + ~$impact (string check, displayed not silently asserted) |
| 10b | **Epilogue — the cycle continues** | `/recommendations` | `addressed-section` | proof: regenerate → `addressed_opportunities` contains the completed opportunity ("this opportunity won't be re-issued — it was addressed") |

Spec's 10 steps map 1:1 (propagation is one spec step rendered as three stops, epilogue is
§13.5's regeneration made visible); the overlay displays them as 12 stops of a 10-chapter story.

`data-story-target` attributes to add (attribute-only edits): predictions workspace
(revenue-decline card, contributions block), advisor-360 (AI insight card, revenue KPI),
recommendations workspace (top rec card, compliance chip, action row, learning-state section,
addressed section), impact-ledger (table), revenue-analytics (total-revenue KPI), dashboard
(revenue rollup KPI), ai-assistant (chat input).

### 2.5 Replayability — same-process reset (the one new mechanism)

New endpoint `POST /recommendations/lifecycle/reset/{advisor_id}` →
`RecommendationLifecycleService.reset_advisor(advisor_id)`:
1. **Refuse anchored advisors**: 403 for `A001`/`A020` (module constant `ANCHORED_ADVISORS`) —
   the guardrail enforced structurally, not by convention.
2. Delete the advisor's rows from the three lifecycle tables + `source='recommendation_lifecycle'`
   memories (exactly what `verify_section13_lifecycle.py::reset_advisor` already does).
3. **Remove the injected runtime artifacts from the in-memory store** — the piece the script
   couldn't do without a restart (fact 0.8): add `remove_vertex(vertex_type, vertex_id)` to the
   mock client/foundation store that deletes the vertex from `store.vertices` and strips its
   entries from `out_index`/`in_index` (both directions). The reset calls it ONLY for vertices
   whose id starts with `TXIMP_` and belongs to this advisor (resolved from the ledger rows read
   in step 2, before deletion) plus their two edges. Structurally incapable of touching seed data
   — the id prefix is the filter, and it is asserted (`assert vid.startswith("TXIMP_")`).
4. Recompute + persist the advisor's feature snapshot (now back to base — e.g. A005 → 406375.14).
5. Return `{advisor_id, ledger_entries_removed, transactions_removed, snapshot_revenue_ltm}` so
   the launch page can display "reset verified: base $406,375.14" as real evidence.
Also mirror: re-set the opportunity vertex's `status` from `ADDRESSED` back (merge-upsert
`{"status": "OPEN", "addressed_by_recommendation_id": ""}`) so regeneration re-issues the rec.
Honest note for the UI + PROGRESS.md: the reset does NOT rewind the bandit weight or GNN
fine-tune — learning history is intentionally cumulative (resetting it would falsify §11.2's
"the system gets smarter over time" story); the launch page says so in one line.

---

## 3. 13B.3 — Division-leader journey (second scenario in the same engine)

Same `StoryStep[]` format, same overlay — a second entry in `scenarios.ts`. Persona/scope only;
no new backend. Steps (division `{D}` = the division containing the scenario advisor, resolved at
launch from `fetchHierarchyTree()`; overlay sets `shell.setPersona("DDW")` at start so the ACTIVE
VIEW card and persona-conditional UI behave correctly):

| # | Title | Route + scope | Real data / action |
|---|---|---|---|
| 1 | **The division view** | `/dashboard`, scope Division {D} | proof: `GET /scope/dashboard?scope_type=DIVISION&scope_id={D}` → real rollup totals; highlight division AI Insight (`GET /scope/ai-insight` — real cross-advisor rollup reasoning, §11.6) |
| 2 | **Who needs attention** | `/dashboard` | highlight `bottom-advisors-table` (real `bottom_advisors` with stated reasons — `ScopeRollupService._top_advisors(ascending=True)`, fact 0.9); overlay picks the top bottom-advisor `{B}` from the live response (fully data-driven, not hardcoded) |
| 3 | **Drill into the advisor** | `/advisor-360`, scope Advisor {B} | proof: {B}'s real KPIs + AI insight — the same diagnosis capability, now entered from the leader's view |
| 4 | **A division-level coaching action** | `/coaching-reviews`, scope Advisor {B} | ACTION: `POST /coaching/tasks` (real §9.5 manager-task CRUD; task from `GET /coaching/task-catalog`, assigned_by "DDW story-mode"); proof: task appears with status, and narration notes it becomes real AI-Assistant context (the §9.5 read path) |
| 5 | **Act on the advisor's top recommendation as the manager** | `/recommendations`, scope Advisor {B} | ACTION: accept+complete via `/feedback-learning/submit` (actor is the manager persona) — reuses the Advisor-journey action machinery verbatim |
| 6 | **The division rollup moved** | `/dashboard`, scope Division {D} | proof: division `totals.revenue_ltm == baseline + impact` (baseline captured at step 1 — the §13.3 propagation math holds at any rollup level since division totals are Σ advisor snapshots) |
| 7 | **Ask as the leader** | `/ai-assistant`, scope Division {D} | pre-filled "Which of my advisors need attention, and what was just completed?" — real rollup-scope answer (11.6 scope-aware path); proof: answer names real advisors incl. {B} and the recorded impact |

Advisor {B} inherits the anchored-advisor guard: if the live bottom-advisor happens to be
A001/A020, the overlay picks the next non-anchored one and says so in the narration ("skipping an
anchored verification advisor"). Honest and self-documenting.

---

## 4. 13B.4 — Business Impact & ROI view (the second genuinely new surface)

### 4.1 Route, nav, and how it differs from the two adjacent existing pages

- Route `frontend/app/(dashboard)/business-impact/page.tsx` → component
  `frontend/components/business-impact/business-impact-workspace.tsx`.
- Nav entry, group `"Executive"` (this is the buyer's closing view, not an AI-lab page), placed
  after Revenue Analytics: `{id: "business-impact", label: "Business Impact & ROI",
  description: "Cumulative, recorded platform impact: revenue driven, recommendations acted on,
  acceptance and completion rates — from the real impact ledger.", href: "/business-impact",
  iconName: "BadgeDollarSign", group: "Executive", status: "new"}`.
- Positioning vs existing pages (state this in each page's subtitle to prevent confusion):
  `/impact-ledger` = the per-entry audit trail (every transaction, every note);
  `/recommendation-roi` = the learning/feedback analytics per advisor;
  `/business-impact` = the executive aggregate — "what has the platform driven, in dollars."
  Cross-link all three.

### 4.2 Data sources (real; one small additive backend extension)

- `GET /impact-ledger` — `totals.total_impact / completed_count / advisors_affected / by_family /
  by_advisor` + entries (for the cumulative-over-time chart, bucketed by `created_ts`).
- **Additive extension** to the same response: `totals.lifecycle_totals` = per-status counts
  across ALL advisors from `phx_dm_local_recommendation` (`SELECT status, COUNT(*) … GROUP BY
  status`) — this is what real acceptance/completion rates need. Existing keys untouched
  (fact 0.12). Rates computed as: acceptance = (ACCEPTED+IN_PROGRESS+COMPLETED+MODIFIED) /
  all-actioned; completion = COMPLETED / (ACCEPTED+IN_PROGRESS+COMPLETED). Denominator
  definitions rendered in the card footnote — never an unexplained percentage.
- `GET /feedback-learning/impact-trend` — the cumulative accepted/implemented/rejected
  trajectory replayed from the real seeded+live feedback history (labeled as such).
- `GET /feedback-learning/state` + `/outcome-learning` — learning families and weights for the
  "the system is learning from this" strip.

### 4.3 Layout (shared design system only — KPI stat cards, Recharts, delta component, currency util)

1. **Four KPI cards**: Cumulative Recorded Impact (`+$…`, green, footnote "sum of real ledger
   transactions TXIMP_*"), Recommendations Acted On (lifecycle_totals actioned count),
   Acceptance Rate %, Completion Rate %.
2. **Cumulative impact over time** — Recharts area/step chart from ledger entries (x =
   `created_ts` date, y = running Σ `impact_amount`).
3. **Impact by action family** (bar, `totals.by_family`) and **by advisor** (bar,
   `totals.by_advisor` with real advisor names).
4. **Feedback trajectory** — line chart from `/impact-trend` (labeled "replayed from real
   recorded feedback history").
5. **Business-outcome mapping strip** (poster language, §11.11 pattern): Increase Revenue ←
   cumulative recorded impact; Increase Advisor Productivity ← completion rate; Improve Goal
   Attainment ← AGP-family share of impact (`by_family`); Increase NCF / Increase AUM ← honest
   status chip "recorded impact is currently revenue-typed; the ledger's `impact_type` column
   supports NCF/AUM entries when those recommendation families record them" — truthful about the
   `impact_type TEXT DEFAULT 'REVENUE'` column, no fake NCF/AUM numbers.
6. **Honest empty state** (the ledger is EMPTY right now, fact 0.2 — this page's first render
   will hit it): when `completed_count == 0`, cards show `$0 / 0 / —` with a panel: "No
   recommendations have been completed yet. Impact appears here the moment one is — run the
   Guided Story Mode to see the full cycle." (link `/story`). The feedback-trajectory chart still
   renders (real seeded history exists) with its source labeled — nothing pretends to be ledger
   data.
7. Evidence footer: sources named (`phx_dm_local_impact_ledger`, `phx_dm_local_recommendation`
   status counts, feedback replay) — the build-standard evidence bar.

---

## 5. 13B.5 — Verification plan (same bar as §13.8)

`scripts/verify_section13B_story.py` + Playwright, evidence to `docs/qa_screenshots/section13B/`
(project-relative, per the standing screenshot rule).

**A. Pipeline-trace real-artifact check (API level, asserted):**
1. `POST /recommendations/generate/A005` → take top rec id.
2. `GET /explainability/pipeline-trace/{rec_id}` → assert all 6 stages present with non-empty
   artifacts; cross-check stage values against their independent sources:
   `stages.features.artifact.top_features[revenue_ltm]` == `GET /advisor/360/A005`
   `feature_snapshot.features.revenue_ltm`; `stages.model.artifact.score` == the chain
   prediction vertex's score; `stages.derivation…estimated_revenue_impact` == the rec payload's;
   `stages.context_compliance.artifact.compliance.status` == the rec payload's new `compliance.status`.
3. `GET /observability/stage-spans` → assert ≥1 span exists (was empty before 13B — before/after
   is itself evidence, capture both).
4. Playwright: `/memory-explainability` → screenshot `s13b-trace.png` (6 stage cards + SYSTEM
   TRACE bar + one expanded stage with real values).

**B. Guided Advisor Journey — one continuous real trace (the headline):**
Reset A005 (`POST …/lifecycle/reset/A005`, record the returned base 406375.14), then drive the
overlay through all 12 stops via Playwright, screenshotting each (`s13b-step01.png` …
`s13b-step12.png`). Assert at the API level in parallel: step 6's returned `impact_amount`, step
7's ledger equality, steps 8a-c's exact `baseline + impact` (to the cent), step 9's weight
before/after, step 10b's `addressed_opportunities`. Step 10's real-Claude answer: run with
`LLM_CLIENT_MODE=claude`; if `ANTHROPIC_API_KEY` is still absent (the §13.4 documented blocker),
record the assembled-context evidence (`GET /ai-chat/context-trace` showing the
RECOMMENDATION_LIFECYCLE item with the real note) and state the same honest blocker line — do
NOT substitute a mock answer as if it were the AI-behavior proof.
Then **replayability proof**: reset again, assert ledger empty + snapshot back to base +
addressed opportunity re-issued on regenerate — screenshot the launch page's "reset verified"
line.

**C. Division Journey:** drive stops 1-7; assert the division rollup before/after and the
coaching task's persistence (`GET /coaching/tasks/{B}`); screenshots `s13b-ddw-*.png`.

**D. Business Impact page:** screenshot the EMPTY state first (before B's run, or after the final
reset) — the honest empty state is itself a requirement — then the populated state after a
completion (`s13b-roi-empty.png`, `s13b-roi-populated.png`); assert the page's cumulative figure
== ledger totals endpoint.

**E. Boot check** (build standard): backend imports + route count includes the 2 new endpoints;
`tsc`/`next build` passes with the 3 new component trees.

**Final-state rule:** end the verification run with A005 reset to pristine base (ledger empty,
406375.14) so the client's own first Story-Mode run starts clean — mirror of §13's closing state.
A001/A020 untouched throughout (enforced by the 403 guard, which the script also exercises and
screenshots as evidence).

---

## 6. Implementation checklist (ordered, commit-sized — for the Opus thread)

1. **Compliance on the live rec payload (§1.3).** Validator call in `generate_for_advisor`,
   `compliance` field + SQLite `compliance_status` mirror; compliance chip on the rec card
   (+ `data-story-target="rec-compliance-chip"`). Curl-verify a PASSED and (via a crafted
   rationale check in a python one-liner) a NEEDS_REVIEW verdict. Commit.
2. **Generation stage-timing (§1.2).** Four `stage_timer`s in `generate_for_advisor` +
   `record_stage`. Verify `/observability/stage-spans` non-empty after a generate (before/after
   captured — first-ever real span). Commit.
3. **Pipeline-trace endpoint (§1.1).** `GET /explainability/pipeline-trace/{rec_id}` with the
   6-stage composition, generation-vs-assembly timing basis. Curl-verify the §5.A cross-checks.
   Commit.
4. **`PipelineTraceBar` UI (§1.4)** in the Explainability Explorer + `?rec=` preselect + the
   "How was this produced?" link from the Recommendations inline panel. Screenshot. Commit.
5. **Reset endpoint + store `remove_vertex` (§2.5).** Incl. the A001/A020 403 guard and the
   opportunity un-address. Verify: complete → reset → base figures restored + rec re-issued,
   same process, no restart. Commit.
6. **Story infra (§2.1-2.2).** `StoryModeProvider` (in AppShell) + `StoryOverlay` + highlighter +
   sessionStorage persistence + `/story` launch page + nav entry. Verify overlay survives manual
   navigation. Commit.
7. **`data-story-target` attributes** on the ~10 listed components (attribute-only). Commit.
8. **Advisor Journey script (§2.3-2.4)** with baseline capture + proof checks + the real
   accept/complete action. Manual Playwright pass of all 12 stops. Commit.
9. **Division Leader Journey (§3).** Commit.
10. **Business Impact & ROI page (§4)** + the `lifecycle_totals` additive backend extension +
    nav entry. Screenshot empty + populated. Commit.
11. **`scripts/verify_section13B_story.py` + full §5 evidence run**, screenshots to
    `docs/qa_screenshots/section13B/`, PROGRESS.md updated with real values (incl. the honest
    real-Claude blocker status if the key is still absent), final A005 reset to pristine. Commit.

**Non-goals, stated to keep scope honest:** no generalized per-artifact-type trace endpoints
(recommendation-keyed only, §1.4); no rewinding of learning history on reset (§2.5, deliberate);
no NCF/AUM impact figures until a recommendation family actually records them (§4.3.5); no new
state of any kind beyond the reset helper — every number the overlay shows is fetched from the
same endpoints the pages themselves use.
