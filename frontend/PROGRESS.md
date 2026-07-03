
## Session 1 (continued, autonomous block started 05:36 UTC) — 2026-07-03

### Phase 10 (parts 1-2) — design system + three real pipeline pages

- `frontend/styles/tokens.ts`: named token system (Section 1B) — severity palette 1:1 with
  Severity_Model, AI-accent violet, dense enterprise type scale, Recharts palette.
- Composite patterns (`frontend/components/patterns/`): KpiStatCard, AiContentCard with
  "AI Generated" chip, SeverityBadge, EvidenceTracePills.
- **/recommendations** — live generation via POST /recommendations/generate; feedback buttons
  post to /feedback-learning/submit and regenerate, so learning-driven re-ranking is visible
  in the UI; learning-state panel shows family weights.
- **/features-embeddings** — Feature Lab: 33-feature snapshot table grouped per catalog,
  click-through per-feature lineage inspector, similar-advisors panel with reason features.
- **/memory-explainability** — Explainability Explorer: lineage chain visualization across
  features→prediction→opportunity→recommendation→feedback→outcome→learning, numbered
  reasoning steps, evidence JSON. Backed by new `/explainability/*` router over GQ-029/032/033.
- All three replace PendingRebuild placeholders; tsc + production build green; endpoints
  verified over HTTP against the mock graph.

### Phase 2 live TigerGraph — third real-engine finding + reload/install running

3. Loading jobs ship without `QUOTE="double"` — JSON-bearing columns (features_json,
   reason_json, vector_preview, …) mis-parse on embedded commas; exactly the 16 artifact
   vertex types loaded empty. Fixed mechanically; all 182 jobs recreated with QUOTE and the
   full load re-run. Query create+INSTALL ALL (43 queries, C++ compile — slow on 2 cores)
   queued behind it in the container (`/tmp/install_out.log`).

**Verification for next session** (if install finished): `docker exec tigergraph bash -c
'export PATH=$PATH:/home/tigergraph/tigergraph/app/cmd; gsql "USE GRAPH
iperform_insights_coaching_demo SHOW QUERY *" | grep -c CREATE'` should approach 43; then
run the 43 query cases against `GRAPH_CLIENT_MODE=local_real` (RESTPP on
localhost:14240/restpp) and compare with mock results; then flip the default working mode
to local_real per Section 5 step 2.

Completed this block: Phases 1, 3(mock), 4, 5, 6, 7, 8, 9, 10(parts 1-2); TigerGraph schema
+182 jobs installed live; 3 upstream GSQL fixes identified and applied locally.
In progress: TigerGraph full reload + 43-query INSTALL (background in container).
Known issues / deferred: runtime-family module deletion + orchestration ToolRuntime rewire
(consolidation sweep); /ui-integrated/* removal as remaining pages rebuild; LLMClient wiring
into insights/chat (needs ANTHROPIC_API_KEY in .env for claude mode spot-checks); remaining
nav pages (command centers, revenue intelligence, AGP/CRM pages, graph explorer, knowledge,
admin, Data Health per 3B); foundation-package fixes to upstream.
Next: 1) verify live query install + run cases on local_real; 2) rebuild Advisor 360 +
AI Assistant pages on real APIs; 3) consolidation sweep (delete runtime family, rewire
orchestration); 4) breadth pages + 3B Data Health.
