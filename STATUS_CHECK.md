# STATUS_CHECK — Master Execution Run (Sections 12 → 13 → 13B → 10 → 14)

_Started: 2026-07-06. Main thread: Opus 4.8. Design delegations: `fable-architect` / general-purpose subagent with `model:"fable"`._

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

## §12 ✅ · §13 ✅ · §13B ✅ (all pushed) — now on §10 (remaining) → §14
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
