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
- [ ] REQ-2: 3 figure→model paths documented (traces built; evidence walk below)
- [ ] REQ-3: persona question-set audit (real Claude) — answers + instrumented sources
- [ ] Remaining pages sweep
- [ ] §13B.3 division/market journeys · §10 mentor pairing + AGP ROI

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

## REQ-3 answer audit

(to be appended)
