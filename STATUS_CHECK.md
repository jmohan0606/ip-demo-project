# Status Check — 2026-07-05 — Consolidation sweep: two missed items + follow-ups

The previous pass answered the wrong "4 items" (the old deferred list). This pass completes the
two genuinely-missed sweep items plus the two follow-ups requested.

## Results

1. **Gitignore the runtime SQLite DBs — DONE.**
   - Added `data/feature_store/*.db` and `data/sqlite/*.db` to `.gitignore`.
   - Both were tracked; `git rm --cached` removed them from the index (staged as `D`).
   - Verified: after a fresh write to both DBs (5.7 MB / 4.3 MB), `git status` shows **only the
     staged removal** — no `M` (modified) or `??` (untracked) entries — i.e. the live file
     content is now ignored. `git ls-files` for those globs returns empty (no longer tracked).

2. **`docs/tigergraph_foundation/UPSTREAM_FIXES.md` — DONE.**
   Documents all four real-engine (TigerGraph Community 4.2.3) GSQL/loader defects with symptom,
   root cause, fix applied, and a suggested validator check for each:
   - Finding 1 — trailing `;` after `WITH …` DDL clauses rejected by `gsql -f`.
   - Finding 2 — 182 loading jobs use `$"col"` + `HEADER="true"` without an initialized
     `DEFINE FILENAME`.
   - Finding 3 — missing `QUOTE="double"` on jobs whose CSVs carry quoted JSON columns.
   - Finding 4 — `QUOTE="double"` tokenizer mis-splits fields containing BOTH a `""` escape AND
     an internal comma (5 vertex types); correct path is RESTPP JSON upsert.

3. **Delete `app/services/opportunity_service.py` — NOT deleted; safety check FAILED (reported).**
   The same zero-live-caller gate used for the rest of the sweep does **not** pass here. It has
   **three live consumers**:
   - `app/agents/tools/service_tools.py` (AgentToolbox) → imported by live agent nodes
     (`prediction_agent`, `tigergraph_graph_agent`, `rag_knowledge_agent`) → `/agentic-ai`.
   - `app/ai/chat/context_assembler.py` → `chat_engine.py` → `/ai-chat`.
   - `app/services/recommendation_service.py` (facade).

   My earlier note called it "unwired" — that was accurate only in the narrow sense of *not
   registered directly in a router*; it is in fact reachable from the live agentic + chat
   pipelines. Deleting it as-is would break the backend import chain. Per the sweep's rule
   (delete only with zero live callers), it is **left in place**. Repointing those three
   consumers from the legacy `OpportunityService` (which reads the old `FeatureStoreService` and
   returns zeroed features) to the live `OpportunityDetectionService` is a separate,
   behavior-changing refactor — flagged for a scoped follow-up, not done blindly here.

4. **Final build + boot check — PASS.**
   - Backend: `import app.api.main` OK — **36 routes** (unchanged from the prior sweep commit;
     no routers touched this pass).
   - Frontend: `tsc --noEmit` PASS; `npm run build` compiled successfully, 25/25 static pages.

## Net file changes this pass

- `.gitignore` — added the two DB globs.
- `data/feature_store/iperform_features.db`, `data/sqlite/iperform.db` — untracked
  (`git rm --cached`).
- `docs/tigergraph_foundation/UPSTREAM_FIXES.md` — new.
- `app/services/opportunity_service.py` — unchanged (retained; see item 3).
