# UI_INTELLIGENCE_WORK — running log for the "visible intelligence" task (2026-07-07)

**Task:** (REQ-1) match the Hackathon mockup exactly with scope-aware content, (REQ-2) make the
AI/ML/graph reasoning behind every figure user-reachable, (REQ-3) the AI/agent layer answers any
reasonable question per persona from FULL context — dashboard first, then the same philosophy as
the standing pattern for all pages. Real Claude for all AI verification. Evidence per item.

Session model: Fable 5 (main thread).

---

## REQ-1 — Element-by-element diff: current Executive Dashboard vs Hackathon mockup

Mockup viewed directly (`docs/spec/mockups/Hackathon UI Mock Up.png`). Current implementation:
`frontend/components/command-center/executive-dashboard.tsx` + `app/scope/{dashboard,insight}.py`.

| # | Mockup element | Current state (verified live) | Gap class | Action |
|---|---|---|---|---|
| 1 | Filter bar: Hierarchy / Advisor / Time Period / Refresh + "Last refreshed" note | Shell filter bar exists (§12.2 rebuilt) | verify | Re-verify during screenshots |
| 2 | KPI tiles: colored icon in soft circle + bold value + green/red arrow delta % + **"vs PY: $X"** absolute prior line | Icons ✓; delta on Revenue tile only; **no vs-PY absolute line anywhere** | build | Per-tile delta_pct + prior value from real prior-period computation; omit (never fabricate) where no real prior exists |
| 3 | **Scope-aware tile SETS** — advisor scope: Total Revenue, Managed Revenue, Managed Rev %, Households, Revenue/Household (+AGP risk, pipeline); firm/division: rollup tiles | **Same 8 firm-shaped tiles at every scope** — advisor scope shows "Advisors In Scope: 1", "At-Risk Advisors: 0" (exact anti-pattern named in the brief) | build | Backend emits a scope-aware `tiles[]` (id/label/value/delta/prior/why-trace); frontend renders from payload |
| 4 | AI Insight Summary: **bold generated headline + grounded prose paragraph** then color-coded Key Drivers / Watch Outs / What to Monitor | Backend writes a 2-3 sentence `executive_summary`, **frontend never renders it**; no headline; Key Drivers literally repeat the tile numbers | build | Backend: Claude generates headline+narrative from facts BEYOND the tiles (category YoY drivers, peers, markets, predictions); frontend renders headline bold + prose + sections |
| 5 | AI Coaching Card (advisor only): Recommendation / Shoutout / Action Steps / Guideline Basis | Exists advisor-only via `/advisor/360/{id}/ai` | verify | Verify structure + real-Claude content during screenshots |
| 6 | Revenue Trend: current line + **prior-year dashed line**, labeled endpoints | Current-period line only | build | Add real prior-year monthly series (months shifted −12) |
| 7 | Revenue by Product Category donut with **center total $** | RevenueDonut with centerLabel | verify | Confirm center shows $total of period |
| 8 | Revenue Drivers (vs Prior Year) signed horizontal bars | Exists, real YoY math | keep | Add REQ-2 trace |
| 9 | Benchmarking (vs Peers): **metric table You / Peer Avg / vs Peer** | Sibling-scope bar chart at leadership scopes; **advisor scope: "No peer group at this scope"** (explicitly unacceptable — GNN similarity engine exists) | build | Advisor scope: peer group = GNN GraphSAGE similar advisors (`graph-insights/similar`, model `graphsage-v1-ft`, verified live: A002 0.97, A008 0.95, A007 0.91…), metric table You vs Peer-Avg vs-Peer + named peers + why-similar |
| 10 | **Recent Transaction Highlights** table (Date / Household-Account / Product / Revenue Impact / Type) | **Absent entirely** | build | New real query over `phx_dm_revenue_transaction` (15,116 rows) via `transaction_for_advisor/household/product` edges; advisor scope = own txns, leadership = largest recent in scope |
| 11 | Top/Bottom Markets table | Exists (leadership scopes) | keep | — |
| 12 | (REQ-2) every figure exposes its reasoning | Page-level evidence footer only; no per-figure path | build | Shared "why" trace popover on tiles + cards, linking to real model/explainability |

Data availability confirmed live before building: feature snapshot per advisor has
`household_count=6, account_count=12, managed_revenue_ratio, weighted_pipeline_value,
agp_risk_score, revenue_ltm…`; GNN similarity live (`graphsage-v1-ft`, 2280 vectors,
sqlite+cosine verified); 15,116 revenue transactions with full edge links.

## Progress log

- [x] Grounding read (CLAUDE.md, PROGRESS, STATUS_CHECK, mockup, git log)
- [x] Diff table above
- [x] Backend: scope-aware `tiles[]` (`app/scope/tiles.py`), advisor GNN benchmark + recent
      transactions (`app/scope/dashboard.py`), prior-year monthly trend (`app/revenue/analytics.py`),
      insight HEADLINE+BODY narrative w/ GNN-peer + driver facts (`app/scope/insight.py`),
      impact transactions categorized "AI-Recommended Actions" (was "Unclassified")
- [x] Frontend: payload-driven `TileGrid` w/ vs-PY line + WhyTrace popover (REQ-2) on every tile,
      insight headline+prose rendering, GNN peer table (You/Peer Avg/vs Peer + named scored peer
      chips, click→that advisor), Recent Transaction Highlights, dashed Prior-Year trend line
- [x] Screenshots firm + advisor scope — REQ-1 diff lines all closed (see table; every "build" row done)
- [x] AUM net-flows waterfall verified present + populated at firm scope (pending-item check)
- [x] REQ-2: 3 figure→model paths documented + verified with screenshots (below). Also found and
      FIXED a real stale-response race in the dashboard (a slow in-flight FIRM fetch resolving
      after an ADVISOR selection overwrote the advisor's data — request-sequence guards added to
      `load`/`loadAi` in `executive-dashboard.tsx`; the bug was caught on a real screenshot showing
      advisor title with firm tiles).

### REQ-2 figure→model evidence (all user-reachable, 2026-07-07)
1. **Total Revenue tile** → ⓘ popover: "Σ revenue_amount in the selected window; delta vs the real
   month-shifted −12 window" + source (transaction traversal) + link → Revenue Analytics.
   `req2_total_revenue_trace.png`
2. **AGP Risk tile** → ⓘ popover: names the AGP off-track prediction model, links → /predictions,
   where the real model detail lives: XGBoost/TreeSHAP feature contributions (+13.7
   overdue_followup_count etc.), confidence, "How this was derived" steps, artifact IDs
   (PRED_AGPRISK_A001_v2.0 / FS / REASON trace). `req2_agp_risk_trace.png` +
   `req2_predictions_model_detail.png`
3. **Benchmarking vs Peers** → ⓘ popover: "Peer group = the 5 nearest advisors by graphsage-v1-ft
   embedding cosine similarity — learned from the real graph (households, products, CRM, revenue
   patterns)" + per-peer scores on the card itself; peer chips click through to that advisor.
   `req2_benchmark_gnn_trace.png`
- [ ] REQ-3: persona question-set audit (real Claude) — answers + instrumented sources
- [x] Remaining pages sweep (screenshots under `docs/qa_screenshots/session16/sweep/`):
      · **AI Assistant** — REAL GAP FIXED: page pinned every scope to one advisor via
        `useScopedAdvisor` (the exact §11.6 anti-pattern). Now follows the ACTIVE scope with
        persona mapping + scope-adaptive question chips. Verified live in the UI: DDW at Division
        D01 asked "Which of my advisors need attention?" → real Claude named 3 advisors with
        per-advisor evidence, "Data used" line, 8 instrumented context items incl. division-wide
        graph traversal (`assistant_ddw_division_scope.png`).
      · **FormattedAnswer** — markdown tables/headings/rules now render properly (answers with
        metric tables were showing raw pipes).
      · **Revenue Analytics** — Trend Explorer confirmed working (slow load, not broken:
        `trend_explorer_focus.png` shows stacked quarterly bars + AI period drivers); channel
        label truncation fixed (RECOMMENDATION_IMPACT); WhyTrace added to all 4 KPI tiles.
      · **Advisor 360** — WhyTrace added to the 4 KPI tiles; page already philosophy-rich
        (AGP components, similar households/accounts w/ scores, PageRank plain-language card,
        churn column w/ honest caveat).
      · **Opportunities & Recommendations / Recommendation Impact** — verified already exemplary
        (learning-loop formalism, weight trajectories, outcome-driven retraining before/after,
        priority = base × learned weight shown per row). No changes needed.
      · **No purple anywhere** re-verified (grep: zero violet hexes; bars are approved indigo).
      · Smoke: 15/15 pages HTTP 200, backend 142 routes.
- [x] §13B.3 division + market guided journeys — VERIFIED end to end. The frontend wrappers exist
      and launch (`story_launch_scenarios.png`: Advisor 11-step, DDW 9-step, MDW 9-step, all with
      Start buttons; anchored A001/A020 excluded from the pick pool). Real propagation proof, run
      through the journey's actual action chain (reset → generate → ACCEPT → COMPLETE) on M01's
      worst non-anchored advisor A002: recommendation "Close the AGP milestone execution gap",
      recorded impact +$47,053.23 (transaction TXIMP_REC_OPP_AGPRESCUE_A002_v2.0) — LTM revenue
      moved by EXACTLY that amount at all three scopes: ADVISOR/A002 $370,629.83→$417,683.06,
      MARKET/M01 $3,513,329.94→$3,560,383.17, DIVISION/D01 $14,465,441.39→$14,512,494.62.
- [x] §10 mentor/mentee GNN pairing + AGP program ROI — BUILT (`app/agp/mentorship.py`,
      `/agp/mentor-pairing` + `/agp/program-roi`, `MentorshipRoi` on the AGP page).
      Pairing: constrained greedy matching on graphsage-v1-ft cosine (capacity ≤2,
      mentor ≥1.2× mentee revenue, PageRank tie-break) — 8/8 at-risk enrollees matched, each with
      a plain-language rationale. ROI: per-enrollee growth since real enrollment date vs the same
      calendar-window growth of their 5 GNN-most-similar NON-enrolled advisors; caveats stated.
      Screenshot: `agp_mentorship_roi.png`. AUM waterfall verified earlier (firm dashboard).

### REQ-1 diff-closure evidence (2026-07-07)
- Advisor scope now shows: Total Revenue $275.4K (+30.7%, vs PY: $210.7K), Managed Revenue $32.9K
  (+77.5%, vs PY: $18.6K), Managed Revenue % 12% (+3.2pp, vs PY: 8.8%), Households 6,
  Revenue/Household $45.9K (vs PY: $35.1K), AUM, AGP Risk 19.1, Weighted Pipeline $324K, NNM —
  NO firm-shaped tiles. Firm scope shows the rollup set (Revenue $23.8M +5.9%, Managed, AUM $2.1B,
  NNM, Advisors 60, Goal, Risk, At-Risk 8).
- Real Claude insight (advisor): HEADLINE "Strong YTD Growth Offset by Below-Peer Revenue and AUM";
  BODY names drivers (+$50K AI-Recommended Actions, +77.5% Managed Accounts, −34.4% Mutual Funds)
  AND the GNN peer gaps (−16.8% LTM vs peers, AUM −35%) — not a tile restatement.
- Real Claude insight (firm): HEADLINE "AI-Driven Actions Offset Managed Product Weakness, Revenue
  Up 5.9%" with per-category YoY drags and at-risk advisor names.
- Benchmarking at ADVISOR scope = GNN graphsage-v1-ft peer group (Jordan Garcia 0.97, Parker Evans
  0.95, Cameron Bennett 0.91, Skyler Nguyen 0.90, Quinn Hill 0.89) + 6-metric You/Peer-Avg/vs-Peer
  table. "No peer group at this scope" eliminated.

## Screenshots

- `docs/qa_screenshots/session16/dashboard_firm_scope.png` — firm scope, full page (matches mockup structure)
- `docs/qa_screenshots/session16/dashboard_advisor_scope.png` — advisor scope, full page (scope-aware tiles + GNN benchmark)

## REQ-3 answer audit (real Claude, 2026-07-07)

**Context assembler extended first** (`app/ai/chat/context_assembler.py` + `ChatContextSource`):
five missing domains added so any reasonable question has its data available — **AGP Program
Status** (real AGP-004 banded score + components), **CRM Pipeline & Activities** (stages + open
work), **Household Risk (ML)** (household-churn-xgb propensities with the honest quality-gate
caveat), **GNN Peer Benchmark** (graphsage-v1-ft peers + metric gaps), **Feedback Learning State**
(bandit weights + feedback counts). Retrieval stays broad; the question-relevance reranker decides
what reaches the prompt. Duplicate RAG chunks deduped.

**Composition defect found by the audit and FIXED** (`app/ai/chat/chat_engine.py`): with real
Claude, the question-specific answer was appended LAST under "AI generated note", behind generic
boilerplate. Now the real answer LEADS, with a compact grounding footer; the mock path keeps the
deterministic evidence composition. Re-verified post-fix (household-risk + MDW questions below).

**Full 12-question run: `docs/qa_evidence/session16_req3_results.json`** (complete answers +
per-answer instrumented source lists). Summary — every answer 8 context items, persona-correct:

| # | Persona/scope | Question | Grounded? | Key sources used (instrumented) |
|---|---|---|---|---|
| 1 | Advisor A001 | Why is my revenue up; sustainable? | ✓ real figures ($437K LTM, 68% 3m growth, drivers + risks) | GraphReasoning, Opportunities, Insights, GNN Peers, CRM |
| 2 | Advisor A001 | Best next actions? | ✓ overdue follow-ups oldest-first, $405K pipeline, coaching tasks | Recommendations, CoachingTasks, Lifecycle, CRM |
| 3 | Advisor A001 | Which households at risk? | ✓ all 6 households w/ real ML propensities + model caveat (PR-AUC below gate — honest) | **Household Risk (ML)**, GraphReasoning |
| 4 | Advisor A001 | How am I vs peers? | ✓ metric table vs GNN peer avg (−16.8% LTM etc.), names peers | **GNN Peer Benchmark**, AGP, CRM |
| 5 | Advisor A001 | AGP status? | ✓ on_track band, risk 20.3→25.8 components, milestone detail | **AGP Program Status**, Insights |
| 6 | Advisor A001 | What did I complete + impact? | ✓ completed rec + measured +$50K impact w/ transaction id | **Lifecycle**, GraphReasoning |
| 7 | Advisor A020 | vs peers? | ✓ different advisor, different (correct) story: ABOVE peer avg revenue, AGP risk 56.8 | GNN Peers, AGP, Recommendations |
| 8 | Advisor A020 | Best next actions? | ✓ A020-specific: 2 overdue follow-ups, milestone deadline coaching | Recommendations×3, CoachingTasks |
| 9 | MDW M01 | Which advisors need attention, why? | ✓ 3 named advisors w/ per-advisor reasons (A002: 6 open opps, $0 recorded impact; A001: $50K impact but low CRM activity) | Scope rollup (Insights), GraphReasoning (scope traversal), Predictions |
| 10 | MDW M01 | What's driving my market? | ✓ market rollup $3.7M/6 advisors, per-advisor contribution reasoning | Insights (rollup), GraphReasoning, Predictions |
| 11 | DDW D01 | Why lagging; biggest opportunity? | ✓ division rollup 24 advisors/$15.4M, names attention advisors, cross-advisor opportunity | Insights (rollup), GraphReasoning, Memory, Predictions |
| 12 | Knowledge | Off-track AGP policy? | ✓ cites `agp_program_overview.txt` verbatim (attention tier, monthly reviews, written plan <70%) + applies it to the asker's own real status | **Knowledge RAG**, AGP Status, CoachingTasks |

None returned "I don't have that", none defaulted a rollup scope to one advisor (M01→6 advisors,
D01→24 advisors, both with per-advisor traversal facts), and every figure in the answers matches a
retrieved context item.
