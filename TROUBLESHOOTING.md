# Troubleshooting

Real problems hit during this build and how they were solved, for anyone (GitHub Copilot
included) continuing the work. Ordered roughly by how often they bite.

---

## 0. Backend unreachable from the browser — "Degraded / Failed to fetch" (three-part root cause)

This is the single most common "nothing loads in the browser" failure. It has **three** distinct
parts that can each cause it, and they compound. Check all three.

### Part A — backend must bind `0.0.0.0`, NOT `127.0.0.1`, in Codespaces
A backend bound to `127.0.0.1:8000` (loopback only) is **not reachable through Codespaces port
forwarding** — the forwarder/external browser cannot reach a loopback-only socket, so every
browser fetch fails even though `curl http://127.0.0.1:8000/...` works fine inside the container.
Diagnose: `ss -tlnp | grep :8000` — if it shows `127.0.0.1:8000` (not `0.0.0.0:8000`), that's the bug.

**Fix (in place, env-driven so it can't silently regress):**
- `API_HOST` env var, **default `0.0.0.0`** (`app/config/settings.py`). Binding `0.0.0.0` still
  accepts loopback connections, so SSR/internal tooling hitting `127.0.0.1:8000` keeps working.
- `scripts/run_api.sh` uses `--host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"`.
- `python -m app.api.main` runs uvicorn with `settings.api_host`/`api_port` (see the `__main__`
  block in `app/api/main.py`).
- On a client machine that wants loopback-only, set `API_HOST=127.0.0.1` — no code change.
- Launch: `API_HOST=0.0.0.0 python -m app.api.main` (or `bash scripts/run_api.sh`). Confirm with
  `ss -tlnp | grep :8000` → must show `0.0.0.0:8000`.

### Part B — Codespaces port 8000 visibility resets to Private on restart
Public forwarding is required for an external browser to reach the backend. Codespaces **silently
resets forwarded ports to Private** across restarts. Set it back:
```bash
gh codespace ports visibility 8000:public -c "$CODESPACE_NAME"
gh codespace ports visibility 3000:public -c "$CODESPACE_NAME"   # frontend, so the app page loads too
gh codespace ports -c "$CODESPACE_NAME"                          # verify: 8000 shows "public"
```
(Or use the VS Code *Ports* panel → right-click 8000 → Port Visibility → Public.) Note: an
anonymous first visit to a public port shows a one-time GitHub "You are about to access a
development port" interstitial — a logged-in user clicks **Continue** once; it is not an app error.

### Part C — the frontend's browser-side base URL must be the public URL (SSR-vs-browser split)
`frontend/lib/api/client.ts` deliberately uses TWO bases (do not collapse them):
- SSR / route handlers / in-container tooling → `API_BASE_URL_INTERNAL` (default `http://127.0.0.1:8000`).
- **Browser** `fetch` → `NEXT_PUBLIC_API_BASE_URL`, inlined into the client bundle at build/dev time.

In Codespaces `NEXT_PUBLIC_API_BASE_URL` (in `frontend/.env.local`) must be the public forwarded
backend URL: `https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}`. On a
client machine it's the local URL (`http://127.0.0.1:8000`).

**Silent-regression trap:** starting the dev server with a one-off override
(`NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev`, e.g. for a headless screenshot)
bakes loopback into the running bundle — the browser then fetches `127.0.0.1:8000` and fails for
any external browser even though `.env.local` is correct. Restart with a plain `npm run dev` so it
reads `.env.local`. Verify the running process isn't overridden:
`cat /proc/$(pgrep -f next-server|head -1)/environ | tr '\0' '\n' | grep NEXT_PUBLIC_API_BASE_URL`.

### Verify end-to-end (the real browser path)
```bash
FE="https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
BE="https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
# public backend reachable + CORS allows the frontend origin (must be HTTP 200 + ACAO header):
curl -s -D - -o /dev/null -H "Origin: $FE" "$BE/env-health" | grep -iE "^HTTP|access-control-allow-origin"
```
Then open `/env-health` in the browser — it should render CONNECTED/green, not "Failed to fetch".
(Backend CORS already allows `https://*.app.github.dev` via `allow_origin_regex` in `app/api/main.py`.)

## 1. Frontend loads but every panel is empty / "Failed to fetch"

**Cause:** the API base URL differs between server-side rendering and the browser. Inside the
container `127.0.0.1:8000` is always reachable, but a browser on someone else's machine must use
the **public forwarded Codespaces URL**.

**Fix (already in place):** `frontend/lib/api/client.ts` uses TWO bases:
- `API_BASE_URL_INTERNAL` (default `http://127.0.0.1:8000`) for SSR / route handlers / Playwright /
  curl tooling — always correct from inside the container.
- `NEXT_PUBLIC_API_BASE_URL` (the public forwarded URL) for browser-side `fetch` — inlined into the
  client bundle at build/dev time.

**Checklist when panels are empty:**
1. Is the backend running on `:8000`? `curl -s http://127.0.0.1:8000/env-health`.
2. Is port **8000 set to Public** in the Codespaces *Ports* panel? Port visibility silently resets
   to Private after some restarts — this is the #1 recurring cause. Re-set it to Public.
3. Is `frontend/.env.local`'s `NEXT_PUBLIC_API_BASE_URL` the correct current forwarded URL? The
   forwarded hostname can change; a stale value points the browser at a dead/likely-CORS-blocked host.
4. Open `/env-health` — it tells you exactly which dependency is red and why.

## 2. CORS "No 'Access-Control-Allow-Origin'" in the browser console

**Cause:** the browser is fetching an origin the backend doesn't allow. Backend CORS
(`app/api/main.py`) allows only `http://localhost:3000/3001` and `http://127.0.0.1:3000/3001`.

**Fixes:**
- Serving the frontend on any other port → add it to `allow_origins` in `app/api/main.py`.
- For a **headless Playwright screenshot** where the browser can't reach the public forwarded URL,
  start the dev server with `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev` so
  browser fetches hit loopback:8000 (which CORS already allows from :3000). This is exactly how the
  `/env-health` screenshot was captured green.

## 3. `ModuleNotFoundError: No module named 'app'` / `app.main`

- Run with the repo root on the path: `PYTHONPATH=. python3 ...` (or `uv run`). `pyproject.toml`
  sets `pythonpath = ["."]` for pytest.
- The FastAPI app is **`app.api.main:app`**, not `app.main`. Uvicorn:
  `uvicorn app.api.main:app --host 127.0.0.1 --port 8000`.

## 4. The mock graph client's store attribute

The active graph client is a `TieredGraphClient` whose in-memory store is `.store` (not `._store`).
To read seeded/runtime data in a script: `get_graph_client().store.vertices["phx_dm_advisor"]`,
`.all_vertices(vtype)`, `.in_ids(edge, id)`, `.out_ids(edge, id)`, `.vertex(vtype, id)`.

## 5. TigerGraph live install stalls on this hardware (2-core/8GB)

**Symptom:** schema (56V/126E) and the 182 loading jobs install fine and `RealGraphClient`
connects/queries/upserts, but the **43-query `INSTALL QUERY` C++ compilation** crashes/hangs the
GSQL server, and a full edge load wedges after a handful of edges.

**This is a hardware constraint, not a code defect.** The GSQL is structurally validated
(`scripts/validate_*` — every edge/vertex reference resolves). Resolution: develop against
`GRAPH_CLIENT_MODE=mock` (the `FoundationGraphStore` loads all 185 CSVs into memory and every
`@mock_query` mirrors the real GSQL). Live query install is deferred to a bigger box; the adapter
means nothing downstream cares which mode is active. When on a larger machine, use
`GRAPH_CLIENT_MODE=local_real`/`real`.

## 6. GSQL / schema edge cases

- **Two schema trees exist.** The **authoritative** one is `docs/tigergraph_foundation/tigergraph/
  schema/` (+ `data/manifest.json`) — the runtime `FoundationGraphStore` loads ONLY from there. The
  top-level `tigergraph/schema/` is a legacy base-repo mirror; keep it consistent but don't treat
  it as source of truth. Divergence between the two has caused real confusion (e.g. reasoning-trace
  edge names) — cross-check both when changing schema.
- **Edge naming must match between writer, reader, schema, and manifest.** A dead edge
  (`phx_dm_reasoning_used_memory`, written but never in the manifest and never read — readers used
  `phx_dm_reasoning_uses_memory`) made data silently invisible. When adding an edge: declare it in
  the foundation schema + manifest, and make the writer and every reader use the exact same name.
- Validate structurally after any schema change: `python scripts/validate_tigergraph_foundation.py`
  (and the source-of-truth validator). Manifest id_column drives the mock upsert's primary key.

## 7. Duplicate-implementation trap

This repo has repeatedly had **two parallel implementations of the same capability** (feature store,
opportunity service, agent system, reasoning-trace representation). Before building something that
sounds like it should exist, `grep` for it — it may already exist twice. When you find a duplicate:
pick the more complete one, consolidate onto it, delete/redirect the other, and record the decision
in `PROGRESS.md`/`DATABASES.md`. Do NOT keep both "just in case."

## 8. `smart_sdk` guarded-import pattern (client-only package)

`smart_sdk` (JPMC Azure/Fusion + LangGraph re-exports) is **not on public PyPI** — it's only in the
client artifactory. It must therefore be imported **only inside** the adapter that needs it
(`AzureOpenAILLMClient`, `AzureOpenAIEmbeddingClient`, `SmartSdkGuardrailClient`), inside
`__init__`, guarded by `try/except ImportError` that raises a clear, actionable error. This keeps
the app booting in mock/claude/real mode on a machine without it. Same rule for `torch`,
`torch_geometric`, `xgboost`, `shap` (optional ML tier). Never move these imports to module top level.

Native LangGraph construction is isolated in `app/agents/workflows/langgraph_builder.py`; the
`langgraph → smart_sdk.ext.langgraph` import remapping is documented there and in
`SMARTSDK_REFERENCE.md` §4-5. The SmartSDK swap on the client is a one-file edit.

## 9. Embedding dimension mismatch

`EMBEDDING_DIM` must match the active embedding adapter's output AND the TigerGraph `EMBEDDING`
attribute DDL AND the Chroma collection. Local sentence-transformers = **384**; Azure
text-embedding-3-small = **1536** (`-3-large` = 3072). Switching modes requires **rebuilding the
Chroma collection** (a fixed-dim collection can't accept differently-sized vectors) — re-run
`scripts/ingest_sample_knowledge.py`. The Azure embedding client raises loudly on a dim mismatch
rather than corrupting the vector space.

## 10. Background process management in this environment

- `pkill -f "next dev"` inside a **compound command** can kill the wrapping shell before the rest of
  the command runs (the restart then never starts). Run the kill and the restart as separate steps,
  and `disown` the `nohup ... &` so it survives.
- Foreground `sleep` is blocked; poll with a short loop:
  `for i in $(seq 1 30); do curl -s -o /dev/null -w "%{http_code}" URL && break; sleep 2; done`.

## 11. Screenshots must go to `docs/qa_screenshots/`

Never `/tmp` or a scratchpad path — those are wiped on codespace restart (this caused a lost-work
confusion once). `docs/qa_screenshots/` is gitignored but persistent. Capture with Playwright
(`frontend/node_modules` has `playwright`); require it from **inside** `frontend/` so the module
resolves, and point `NEXT_PUBLIC_API_BASE_URL` at loopback (see #2).

## 12. Reasoning / AI-behavior checks need real Claude

Mock LLM output is deterministic/templated by design and **cannot** demonstrate real reasoning,
grounding, continuity, or structured formatting. For any check that claims the system is
"intelligent," run with `LLM_CLIENT_MODE=claude` (real API). Mock is fine only for
pipeline-wiring/data-correctness checks where the prose itself isn't what's being tested.

## 13. `datetime.utcnow()` deprecation warnings

Harmless `DeprecationWarning` noise from `app/shared/ids.py` and Pydantic. Filter it in scripts
(`2>&1 | grep -v -e Deprecat -e utcnow`) rather than chasing it; not a failure.
