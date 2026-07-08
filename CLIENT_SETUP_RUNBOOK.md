# Client Setup Runbook — iPerform Insights & Coaching

A literal, top-to-bottom runbook a developer follows on the **client (JPMC) machine** after
pulling the repo. Every command and file name here is real and taken from the actual repo. Where
something a step needs does **not** exist in the repo, it is flagged explicitly (⚠️ **GAP**).

Companion docs (read alongside, do not duplicate here):
- `CLIENT_ENV_SETUP.md` — the definitive `.env` variable reference (modes, cdao, SmartSDK,
  TigerGraph secret). This runbook sequences and verifies; that doc is the field reference.
- `TROUBLESHOOTING.md` — symptom → fix table; every "if red / if it fails" below points here.
- `SMARTSDK_REFERENCE.md` — confirmed client values (TigerGraph host, Fusion endpoints).
- `DATABASES.md` — what each local store (SQLite, Chroma) holds.

**Legend for verification tags used throughout:**
- ✅ **Verified in codespace** — the exact command (or its testable equivalent) was run here and
  its result is quoted in §12.
- 🔶 **Not testable from codespace** — needs the client network / hardware (live TigerGraph, cdao
  PCL login, `uv`, MCP Tier-1). Verify live on the client machine. `uv` is **not installed** in
  this codespace, so every `uv …` line below is 🔶; the codespace equivalent that was actually run
  is noted next to it.

---

## 0. Fast-path checklist (whole order at a glance)

```
# 1. Repo + environment
git clone <repo> && cd ip-demo-project
uv venv && source .venv/bin/activate          # client uses uv (see §3 for the codespace equivalent)
cp .env.example .env                          # then edit .env  (§2)
cp frontend/.env.local.example frontend/.env.local
# uv.toml is already committed (points at the client artifactory). Confirm it is present.
cp frontend/.npmrc.client-template frontend/.npmrc

# 2. Dependency PRE-CHECK — resolve every MISSING before installing anything (§4)
python scripts/check_client_deps.py
python scripts/check_client_npm.py

# 3. Install (§5)
uv pip install -e ".[cdao,ml]"                 # gds extra is future-only (see §6.4 / GRAPH_ML_AND_GDS.md)
uv pip install smart_sdk                       # client-artifactory only (optional azure fallback)
cd frontend && npm install && cd ..

# 4. TigerGraph: connect -> secret -> schema -> (EMBEDDING/GDS: see §6.4) -> queries (§6)
#    (in GSQL on the TigerGraph host)
CREATE SECRET iperform_insights_coaching_demo         # paste output into TG_SECRET in .env
bash docs/tigergraph_foundation/scripts/install_tigergraph.sh   # schema + loading jobs + 43 queries

# 5. START THE APP + verify CONNECTIVITY FIRST — before loading data or training (§7)
#    PCL AWS login FIRST (cdao needs the ambient session), then:
bash scripts/run_all.sh                        # backend :8000 + frontend :3000 together
#    Open the Connection & Environment Health screen — all green before proceeding.

# 6. Load graph data (§8)  —  in-app "Run All Ingestion", or:
curl -X POST http://127.0.0.1:8000/ingestion/run-all

# 7. Train ML / GNN models (§9)
bash scripts/train/run_all.sh                  # or per-model, see §9

# 8. Final end-to-end verification (§10)
```

If anything below is red, stop and fix it before the next step — do not proceed to a demo with a
red health check.

---

## 1. Prerequisites (client machine, human-provided — not automatable)

| Prereq | Why | Check |
|--------|-----|-------|
| Python **3.10–3.12** (dev/verify on 3.12) | `requires-python = ">=3.10, <=3.14.2"` in `pyproject.toml`; `check_client_deps.py` needs ≥3.11 (`tomllib`). | `python --version` |
| `uv` installed | Client standard installer; resolves `smart_sdk`/`cdao*` from the artifactory. | `uv --version` |
| Node.js **≥18** + npm | Next.js 14 frontend. Verified here on Node 24 / npm 11.9. | `node --version && npm --version` |
| Network reach to the client PyPI + npm artifactory | All Python/JS deps, incl. client-only `smart_sdk`/`cdao*`. | §4 pre-check exits 0 |
| Network reach to the client **TigerGraph** host | `GRAPH_CLIENT_MODE=real`. | §7 health = green |
| **PCL AWS login** ability | cdao LLM + embeddings authenticate from the ambient AWS session (no keys in `.env`). | `LLM_CLIENT_MODE=cdao_openai` health = green (§7) |

None of the client endpoints (TigerGraph, cdao, artifactory) are reachable from the build
codespace — that is expected and is exactly why steps that touch them are tagged 🔶.

---

## 2. `.env` and frontend env — copy templates, then fill (§ maps to `CLIENT_ENV_SETUP.md`)

**PRE-REQ:** repo cloned. **Commands:**

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
```

Set these in **`.env`** for the client (real) configuration. Variable names are taken verbatim
from `.env.example`:

```ini
# --- Adapter modes (the switches that pick real vs mock backends) ---
GRAPH_CLIENT_MODE=real            # tiered client: MCP -> pyTigerGraph -> RESTPP -> Mock fallback
LLM_CLIENT_MODE=cdao_openai       # PRIMARY. Fallback: azure (SmartSDK/Fusion)
EMBEDDING_CLIENT_MODE=cdao_openai # PRIMARY. Fallback: azure
MODEL_CLIENT_MODE=real            # trained ML/GNN artifacts; falls back to deterministic per-model
VECTOR_CLIENT_MODE=local          # local SQLite cosine (default). tigergraph only after §6.4 probe passes

# --- cdao OpenAI (PRIMARY LLM + embeddings). NO keys here — uses the PCL AWS session (§7). ---
CDAO_API_VERSION=2024-02-01
CDAO_WORKSPACE_ID=906313          # from the client console
CDAO_MODEL=gpt-4o-2024-08-06
CDAO_EMBEDDING_MODEL=text-embedding-3-large-1
EMBEDDING_DIM=3072                # REQUIRED for cdao text-embedding-3-large-1 (see note below)

# --- TigerGraph (real connection; getToken(secret) + SSL) ---
TG_HOST=https://wh-110ecdf498.svr.us.jpmchase.net
TG_GRAPHNAME=iperform_insights_coaching_demo
TG_USERNAME=R757680
TG_USE_SSL=true
TG_GS_PORT=14240
TG_SECRET=                        # paste the CREATE SECRET output from §6.2 — never commit
```

> **EMBEDDING_DIM is load-bearing.** `local` sentence-transformers = **384**; cdao
> `text-embedding-3-large-1` = **3072**; azure `text-embedding-3-small` = **1536**. It must match
> the active embedding adapter **and** the Chroma collection **and** the TigerGraph `EMBEDDING`
> DDL. Changing it requires rebuilding the Chroma collection (`scripts/ingest_sample_knowledge.py`).
> The embedding adapter raises loudly on a mismatch rather than corrupting the vector space.

If cdao is unavailable, switch both to the SmartSDK path — `LLM_CLIENT_MODE=azure`,
`EMBEDDING_CLIENT_MODE=azure`, set `EMBEDDING_DIM=1536`, and fill the `AZURE_*` / `FUSION_*` block
(see `CLIENT_ENV_SETUP.md` §1). To also enable local Claude spot-checks, set `ANTHROPIC_API_KEY`.

Set these in **`frontend/.env.local`** (names verbatim from `frontend/.env.local.example`):

```ini
API_BASE_URL_INTERNAL=http://127.0.0.1:8000                 # SSR / tooling — always loopback
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000             # browser — set to the PUBLIC backend URL
```
On a plain client workstation where the browser and backend share the host, the loopback default
is correct. In a forwarded/remote setup (e.g. Codespaces) set `NEXT_PUBLIC_API_BASE_URL` to the
public backend URL and make that port Public.

**CHECK:** `.env` and `frontend/.env.local` exist and are gitignored:
```bash
test -f .env && test -f frontend/.env.local && echo "env files present"
git check-ignore .env frontend/.env.local frontend/.npmrc   # each path should echo back
```
🔶 Real values (secret, workspace id) can only be validated by the health screen in §7.

---

## 3. Python environment (venv)

**Client (uv) — 🔶 not testable here (`uv` not installed in the codespace):**
```bash
uv venv                 # creates .venv/
source .venv/bin/activate      # Linux/macOS.  Windows: .venv\Scripts\activate
```
`[tool.uv] package = false` in `pyproject.toml`, so `uv venv` + `uv pip install -e .` is the
intended flow (not `uv sync` — there is no `uv.lock`, and the committed lockfile is `poetry.lock`).

**Codespace equivalent that WAS run (✅):** this codespace ships a pre-provisioned Python 3.12
with the deps already importable, so no venv step was needed to boot. Verified: `python -c "import
app.api.main"` succeeds (fastapi 0.139.0). On the client machine the venv step above is required.

**CHECK:** `python -c "import sys; print(sys.version)"` shows 3.10–3.12, and (after §5)
`python -c "import fastapi, app.api.main; print('ok')"` prints `ok`.

---

## 4. Dependency PRE-CHECK — run BEFORE installing anything

**PRE-REQ:** on the client network (reaches the artifactory); `.env` optional. **Commands
(names/paths are real):**

```bash
python scripts/check_client_deps.py     # every pyproject group (core/dev/aws/ml/cdao) + smart_sdk
python scripts/check_client_npm.py      # frontend/package.json deps + devDeps
```

- Defaults point at the client artifactory. Override with `--index-url` / `--registry` (or
  `CLIENT_PYPI_INDEX` / `CLIENT_NPM_REGISTRY`).
- Each package prints **AVAILABLE** / **VERSION-MISMATCH** / **MISSING**; at-risk packages print
  their documented fallback.
- **Exit codes:** `0` = pass; `1` = a required dep has an issue; `2` = index unreachable.
- **How to read it:** the four client-only packages (`smart_sdk`, `cdaosmart-sdk`, `cdaosdk-all`,
  `cdaosmart-evals`) will show **MISSING** on public PyPI — that is expected off the client
  network. On the client artifactory they must resolve. Resolve every genuine MISSING /
  VERSION-MISMATCH per the fallback table in `CLIENT_ENV_SETUP.md` §2 **before** installing.

**CHECK:** both scripts exit `0` with `PASS:` on the last line.
✅ Verified in codespace against **public PyPI/npm** (client index unreachable here): deps
`40/44 AVAILABLE` (the 4 client-only packages correctly flagged MISSING, exit 0); npm `28/28
AVAILABLE`, exit 0. See §12.

---

## 5. Install dependencies

**PRE-REQ:** §4 passed; venv active. **Commands (real, from `CLIENT_ENV_SETUP.md` §2):**

```bash
uv pip install -e ".[cdao,ml]"        # core + cdao SDK (PRIMARY LLM/embeddings) + ML/GNN (local PyG)
uv pip install smart_sdk              # client-artifactory only; azure fallback path (guarded import)
cd frontend && npm install && cd ..   # uses frontend/.npmrc (client registry) from §2
```
- `[cdao]` pulls `cdaosdk-all[openai]` (pinned to the `artifacts` index via `[tool.uv.sources]`) —
  serves **both** `cdao_openai` LLM and embedding paths.
- `[ml]` is optional: `app/ml/*` guard `torch`/`torch-geometric`/`xgboost`/`shap` imports and
  fall back to deterministic scorers if absent. The GNN uses **local PyTorch Geometric** (from
  `[ml]`), **not** `pyTigerGraph[gds]` — that `gds` extra is commented out in `pyproject.toml` and
  is needed only for the future native TigerGraph GDS/GNN conversion (see `GRAPH_ML_AND_GDS.md`
  Part 2 and §6.4 below). If `[gds]` fails (when you later enable it), base `pyTigerGraph` still
  connects and the GNN falls back to the local PyG path.
- `smart_sdk` is **intentionally not in `pyproject.toml`** (not on public PyPI); install it
  explicitly, and only if you need the `azure` fallback modes.

**CHECK (✅ the import check was run here; all ML deps present):**
```bash
python -c "import importlib.util as u; \
print({m: bool(u.find_spec(m)) for m in ['fastapi','uvicorn','torch','torch_geometric','xgboost','shap','sklearn','sentence_transformers','chromadb','pyTigerGraph','anthropic','tigergraph_mcp']})"
```
Every value should be `True` (the client-only `smart_sdk`/`cdao*` may be `False` until installed
from the artifactory). Frontend: `ls frontend/node_modules >/dev/null && echo "node_modules ok"`.

---

## 6. TigerGraph — connect → secret → schema → (EMBEDDING/GDS) → queries

> 🔶 **This entire section is not testable from the codespace** (no reachable TigerGraph; `gsql`
> CLI runs on the TigerGraph host). Commands and file paths below are real and verified to exist
> in the repo; run them live on the client machine.

### 6.1 Connect / confirm the engine
On the TigerGraph host: `gadmin status` — all services **Online** before proceeding.

### 6.2 Create the auth secret
In GSQL (the developer has admin access, per `SMARTSDK_REFERENCE.md` §7):
```gsql
CREATE SECRET iperform_insights_coaching_demo
# -> The secret: <SECRET_STRING> has been created for user "R757680".
```
Paste `<SECRET_STRING>` into `.env` as `TG_SECRET` (TigerGraph cannot restore it later). The app
converts it to a REST++ token via `getToken(secret)` on first connect.

### 6.3 Install schema, loading jobs, and queries — **authoritative path**
Use the verified foundation package installer (real file, confirmed present):
```bash
bash docs/tigergraph_foundation/scripts/install_tigergraph.sh
```
It runs, in order (all real files):
1. `docs/tigergraph_foundation/tigergraph/schema/00_install_schema.gsql`
   → `@01_vertices.gsql` (60 vertex types), `@02_edges.gsql` (directed + reverse edges),
   `@03_create_graph.gsql` (`CREATE GRAPH iperform_insights_coaching_demo`).
2. `docs/tigergraph_foundation/tigergraph/loading/install_all_loading_jobs.gsql` (the loading
   jobs — one per vertex/edge target).
3. `docs/tigergraph_foundation/tigergraph/queries/install_all_queries.gsql` (the GQ-### query
   catalog; 51 `.gsql` files present in that dir).

> **Note — two TigerGraph layouts exist in the repo; use the foundation one above.** There is a
> second, older/smaller layout at the repo-root `tigergraph/` (20 queries in `queries_v1/`, one
> loading job) with installer `scripts/install_tigergraph_source_of_truth.sh`. The **foundation
> package** (`docs/tigergraph_foundation/…`, referenced by `.env`'s `FOUNDATION_DIR` and
> `CLIENT_ENV_SETUP.md`) is the source of truth — prefer §6.3. Do not run both.

### 6.4 EMBEDDING attribute + GDS (native TigerVector / graph algorithms) — ⚠️ **GAP, read carefully**
**Honest finding after inspecting the repo:** there are **NO** `ALTER VERTEX … ADD EMBEDDING`,
`EMBEDDING(DIMENSION=…, METRIC="COSINE")`, HNSW, or GDS-algorithm-install (`Featurizer`,
PageRank/Louvain) `.gsql` scripts anywhere in `tigergraph/` or `docs/tigergraph_foundation/`. The
`phx_dm_embedding` vertex stores embedding **metadata** (`dimensions INT`, `vector_preview STRING`)
— not a native vector column. So there is nothing to "install" here as a script, and this runbook
does **not** point you at one.

How native vectors / graph algorithms are actually handled (all in Python, adapter pattern):
- **Vectors:** `app/ml/vector_client.py` — `VECTOR_CLIENT_MODE=local` (default) uses SQLite
  brute-force cosine (fine at ~1.1K vectors). `VECTOR_CLIENT_MODE=tigergraph`
  (`TigerGraphVectorClient`) issues the native `EMBEDDING`/HNSW/`vectorSearch` GSQL **at runtime**
  and is only used **after** its support is confirmed empirically.
- **Graph algorithms:** `app/ml/graph_algorithms.py` computes PageRank ("Referral Network
  Position") and Louvain ("Peer Communities") with **networkx** over the in-memory store; the
  TigerGraph-native GDS `Featurizer.installAlgorithm` path is documented as a bigger-box fallback,
  not shipped as scripts.
- The GNN (GraphSAGE) likewise runs on **local PyTorch Geometric**, not `pyTigerGraph[gds]`.

> **Native-conversion guide:** `GRAPH_ML_AND_GDS.md` (repo root) is the authoritative reference for
> what runs natively-in-TigerGraph vs. in-Python today (Part 1) and the exact step-by-step to
> convert graph algorithms + GraphSAGE + vectors to native TigerGraph GDS/GNN on the client machine
> (Part 2 — the only situation that needs the `pyTigerGraph[gds]` extra; it is commented out in
> `pyproject.toml` until then).

**What to do on the client machine (optional, deferred — not required for the demo):**
```bash
bash scripts/check_tg_vector_support.sh      # probes whether the engine accepts EMBEDDING DDL
```
- **PASS** → you may set `VECTOR_CLIENT_MODE=tigergraph` (the code will create/use native vectors).
- **UNVERIFIED/FAIL** (expected on 2-core CE 4.2.3, same C++ INSTALL limit as elsewhere) → keep
  `VECTOR_CLIENT_MODE=local`. This is a fully supported, documented outcome — not a blocker.
🔶 Not testable here (needs the Docker TigerGraph container).

### 6.5 Reset / rebuild the schema (clean teardown + recreate)
To tear the schema down completely and recreate it clean (e.g. a corrupted load, a schema change,
or a fresh start on the client machine), use the real drop script (created for this repo):

```bash
# ⚠️ DELETES ALL SCHEMA + DATA for graph iperform_insights_coaching_demo — no undo.
gsql docs/tigergraph_foundation/tigergraph/schema/99_drop_all.gsql
```
`99_drop_all.gsql` drops, in TigerGraph-correct order, the graph → all **133** forward edge types
(each reverse edge auto-drops with its forward edge — reverse edges cannot be dropped alone) → all
**60** vertex types, all at `USE GLOBAL` scope. The object lists were derived programmatically from
the actual `01_vertices.gsql` / `02_edges.gsql` (not a hand-typed guess), so they stay complete and
in sync. A `DROP ALL` one-liner alternative (nukes the entire TigerGraph catalog) is documented in
the file header for single-purpose instances.

**Recreate afterward — exact sequence** (in the schema dir, or via the §6.3 installer for steps
1–3):
```bash
cd docs/tigergraph_foundation/tigergraph/schema
gsql 01_vertices.gsql          # 60 vertex types
gsql 02_edges.gsql             # 133 forward edges (+ reverse edges)
gsql 03_create_graph.gsql      # CREATE GRAPH iperform_insights_coaching_demo
gsql ../queries/install_all_queries.gsql   # reinstall GQ-### queries
# then reload data: app "Run All Ingestion" (§8) or ../loading/run_all_loading_jobs.sh
```
Usable both in codespace-adjacent tooling (against a local Docker TigerGraph) and on the client
machine. 🔶 The GSQL was **structurally validated** (complete + correctly ordered, drop lists match
the CREATE scripts exactly) but not executed here — **verify live on the client machine / a real
TigerGraph** (no reachable engine in the codespace).

**CHECK for §6 overall:** schema/queries install without GSQL errors; the §7 health screen shows
TigerGraph green with real vertex/edge type + row counts.

---

## 7. START THE APP + verify CONNECTIVITY / HEALTH — **before loading data or training**

**PRE-REQ:** §5 installed; §6 schema installed; `.env` filled. **CRITICAL ORDER PREREQ — run the
PCL AWS login FIRST**, in the same shell that will start the backend (cdao LLM + embeddings have no
keys in `.env`; they use that ambient AWS session; one login covers both). If it expires, cdao
calls fail at request time — re-login and restart.

### 7.1 (Recommended first) mock boot — isolates app issues from connectivity
```bash
GRAPH_CLIENT_MODE=mock LLM_CLIENT_MODE=mock EMBEDDING_CLIENT_MODE=local \
  python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```
✅ Verified in codespace: serves; `GET /health/runtime` returns the app report; `GET
/graph-access/health` shows `active_mode: mock`; `GET /env-health` returns `overall: green`;
OpenAPI exposes **146** routes.

### 7.2 Real boot — the combined launcher (starts backend + frontend together)
```bash
bash scripts/run_all.sh
```
- Backend → `http://0.0.0.0:8000` (docs at `/docs`); frontend → `http://localhost:3000`.
- Uses `uv run uvicorn …` when `uv` is present; otherwise falls back to `python -m uvicorn …`.
- Override ports with `API_PORT` / `UI_PORT`, host with `API_HOST`.
- ✅ **Created and verified in codespace** (this was a gap — no combined launcher existed before;
  only separate `scripts/run_api.sh` and `npm run dev`). Verified: backend `HTTP 200` on
  `/health/runtime`, frontend `HTTP 307` (Next.js root redirect) — both via the one script.

To run them separately instead: backend `bash scripts/run_api.sh` (or the uvicorn line in §7.1
with real modes); frontend `cd frontend && npm run dev`.

### 7.3 Connection & Environment Health screen — the gate
Open the **Connection & Environment Health** page in the UI, or:
```bash
curl -s http://127.0.0.1:8000/env-health | python -m json.tool
```
It actively checks (each green/red with the real error if red):
- **TigerGraph** — reachable, auth/SSL, graph present, schema installed, per-vertex-type row counts.
- **LLM** — a real test generation (latency + response) via the active adapter (cdao/azure).
- **Embedding** — a real embed + the configured `EMBEDDING_DIM`.
- **Chroma** — reachable + collection count.

For the tiered graph adapter specifically (`GRAPH_CLIENT_MODE=real|auto|tiered|mcp`):
```bash
curl -s http://127.0.0.1:8000/graph-access/health
```
🔶 Live TigerGraph/cdao greens are not testable here — confirm on the client machine.

**CHECK:** `env-health` `overall` = `green`. **Do not proceed to §8 until it is.** If red, the
payload names the real cause — fix per `TROUBLESHOOTING.md` and re-check.

---

## 8. Load graph data (only after §7 is green)

Two equivalent paths — pick one:

**A. In-app "Run All Ingestion" (recommended — no `gsql` CLI needed; RESTPP upserts remotely):**
UI → **Data Ingestion & Sync** → **Run All Ingestion**, or:
```bash
curl -X POST http://127.0.0.1:8000/ingestion/run-all      # background worker, manifest order
curl -s  http://127.0.0.1:8000/ingestion/run-all/status   # poll until complete
```
✅ Endpoints verified present in codespace (`/ingestion/run-all`, `/ingestion/run-all/status`).
Loads the **192** manifest CSVs (`docs/tigergraph_foundation/data/manifest.json`, graph
`iperform_insights_coaching_demo`, batch size 500) from `data/sample/{vertices,edges}/`.

**B. Server-side GSQL loading jobs (on the TigerGraph host, after staging the CSVs there):**
```bash
bash docs/tigergraph_foundation/tigergraph/loading/run_all_loading_jobs.sh /home/tigergraph/iperform-data
```
🔶 Not testable here.

**CHECK:** `env-health` TigerGraph `row_counts` are non-zero and match manifest expectations
(the `run-all/status` payload reports per-entity counts and mismatches).

---

## 9. Train ML / GNN models

**PRE-REQ:** `[ml]` installed (§5) — the GNN trains on **local PyTorch Geometric**, not
`pyTigerGraph[gds]`; graph data available (mock is fine for training — the
trainers read the FoundationGraphStore / feature store); `MODEL_CLIENT_MODE=real` so artifacts are
written. Set `ML_TIME_BOX_MINUTES` (default 10) as a per-step wall-clock cap on slow hardware.

**Run everything (orchestrator — ✅ created in this task):**
```bash
bash scripts/train/run_all.sh
```
Runs every trainer in dependency order with `PYTHONPATH=.` set and tolerant of a missing optional
dep (skips only that step). Existing `scripts/train/run_all.py` covers only the 3 tabular
classifiers — the new shell orchestrator covers **all** models below.

**Or per-model, in this exact order** (all real files under `scripts/train/`; each is
re-runnable, prints real metrics, and asserts the anchored A001 figures — run from repo root with
`PYTHONPATH=.`):

| # | Command | Trains | Backing module | Needs |
|---|---------|--------|----------------|-------|
| 1 | `PYTHONPATH=. python scripts/train/train_revenue_decline.py` | REVENUE_DECLINE_RISK | `app.ml.training.classifiers` | xgboost |
| 2 | `PYTHONPATH=. python scripts/train/train_household_churn.py` | household churn | `app.ml.training.classifiers` | xgboost |
| 3 | `PYTHONPATH=. python scripts/train/train_agp_off_track.py` | AGP_OFF_TRACK_RISK | `app.ml.training.classifiers` | xgboost |
| 4 | `PYTHONPATH=. python scripts/train/train_revenue_forecast.py` | monthly revenue forecast | `app.ml.forecast` | torch |
| 5 | `PYTHONPATH=. python scripts/train/train_graphsage_embeddings.py` | GraphSAGE node embeddings | `app.ml.gnn` | **torch-geometric** |
| 6 | `PYTHONPATH=. python scripts/train/train_anomaly_detector.py` | activity anomaly (IsolationForest) | `app.ml.anomaly` | sklearn |
| 7 | `PYTHONPATH=. python scripts/train/train_fl_finetune.py` | outcome-driven GNN fine-tune (§11.3) | `app.ml.fl_finetune` | torch-geometric |

> **`PYTHONPATH=.` is mandatory** — without it the scripts fail with `ModuleNotFoundError: No
> module named 'app'`. The orchestrator sets it for you.

**GNN fallback:** the GNN runs on **local `torch-geometric`** today (not `pyTigerGraph[gds]`). If
`torch-geometric` is unavailable, steps 5 & 7 skip and similarity falls back to deterministic
feature-projection — `MODEL_CLIENT_MODE` still works, just without the GraphSAGE artifact. The
native `pyTigerGraph[gds]` `neighborLoader` path is a future client-machine conversion only
(`GRAPH_ML_AND_GDS.md` Part 2). The orchestrator reports which steps were skipped.

**Artifacts land in:** `models/artifacts/*.joblib | *.pt`; registry at `models/registry.json`.

**CHECK (✅ step 1 verified end-to-end in codespace):** step 1 printed real metrics
(`test roc_auc = 0.7755 (floor 0.65) -> PASS`) and `anchor check OK — A001 revenue_ltm=387293.22
…`, and wrote artifacts under `models/artifacts/`. Confirm `models/registry.json` gains entries
after a run.

---

## 10. Final end-to-end verification

**PRE-REQ:** §7 green, §8 loaded, §9 trained. Run these on the client machine:

1. **Boot + routes:** `curl -s http://127.0.0.1:8000/openapi.json | python -c "import sys,json;print('routes:',len(json.load(sys.stdin)['paths']))"` → ~146.
2. **Health all-green (real modes):** `curl -s http://127.0.0.1:8000/env-health` → `overall: green`
   (TigerGraph + cdao LLM + embeddings + Chroma).
3. **Adapter/tier proof:** `curl -s http://127.0.0.1:8000/graph-access/health` → `active_tier` /
   `active_mode` shows the live tier serving (not `mock`), per `CLIENT_ENV_SETUP.md` §3b.
4. **Data present:** `env-health` row counts non-zero.
5. **AI real, not mock:** with `LLM_CLIENT_MODE=cdao_openai`, ask the AI Assistant a real question
   and confirm a grounded, non-templated answer (per the build's standing rule: AI-behavior checks
   use a real LLM, never mock).
6. **Frontend:** open `http://localhost:3000`, confirm pages render with real data and no console
   errors; the Connection & Environment Health page is all green.

**Section-14 handover config** (client's own hands-on testing, "no mock anywhere"):
`GRAPH_CLIENT_MODE=real` (or `local_real`), `LLM_CLIENT_MODE=claude` or `cdao_openai`,
`EMBEDDING_CLIENT_MODE=cdao_openai`, `MODEL_CLIENT_MODE=real`. Confirm the backend boots and serves
in this configuration before handing over (verify it, don't assume).

---

## 11. Troubleshooting

All symptom → fix detail lives in **`TROUBLESHOOTING.md`**. Quick pointers:
- **Backend unreachable from the browser** → bind `0.0.0.0` (the launcher default), make the
  forwarded port Public, set `NEXT_PUBLIC_API_BASE_URL` to the public URL. (TROUBLESHOOTING.md)
- **`ModuleNotFoundError: No module named 'app'`** when training → run from repo root with
  `PYTHONPATH=.` (or use `scripts/train/run_all.sh`).
- **cdao calls fail at request time** → PCL AWS session expired; re-login, restart the backend.
- **Embedding dim mismatch / Chroma errors after switching modes** → set `EMBEDDING_DIM` to match
  the adapter and rebuild the collection: `python scripts/ingest_sample_knowledge.py` (§2 note).
- **A dep is MISSING in §4** → fallback table in `CLIENT_ENV_SETUP.md` §2.
- **TigerGraph tier red / falls back to mock** → the `graph-access/health` payload names the real
  auth/SSL/host cause; fix `.env` `TG_*` per §6.2 and `CLIENT_ENV_SETUP.md` §3.

---

## 12. Verification report (what was actually done for this runbook)

### (a) Commands actually run in the codespace + result

| Command (or codespace equivalent) | Result |
|-----------------------------------|--------|
| `python -c "import fastapi, app.api.main"` | ✅ imports; fastapi 0.139.0 |
| ML dep `find_spec` check (torch, torch_geometric, xgboost, shap, sklearn, sentence_transformers, chromadb, pyTigerGraph, anthropic, tigergraph_mcp, uvicorn) | ✅ all `True` |
| `python -m uvicorn app.api.main:app` (mock modes) + `curl /health/runtime` | ✅ serves; report returned |
| `curl /graph-access/health` | ✅ `active_mode: mock`, manifest counts returned |
| `curl /env-health` | ✅ `overall: green` (mock) |
| `curl /openapi.json` route count | ✅ **146** paths |
| `python scripts/check_client_deps.py --index-url https://pypi.org/simple` | ✅ exit 0; `40/44 AVAILABLE`, 4 client-only correctly MISSING |
| `python scripts/check_client_npm.py --registry https://registry.npmjs.org` | ✅ exit 0; `28/28 AVAILABLE` |
| `PYTHONPATH=. MODEL_CLIENT_MODE=real python scripts/train/train_revenue_decline.py` | ✅ trained; test roc_auc 0.7755 PASS; anchor A001 OK; artifact written |
| `bash scripts/run_all.sh` (ports 8013/3013) | ✅ backend HTTP 200, frontend HTTP 307 — both up |
| `bash scripts/train/run_all.sh` (through step 1) | ✅ dispatches with PYTHONPATH; step 1 trained |
| `curl /ingestion/run-all` route existence | ✅ endpoint present (not executed live) |

### (b) Scripts created for this runbook
- `scripts/run_all.sh` — combined backend+frontend launcher (none existed before). Tested ✅.
- `scripts/train/run_all.sh` — full ML/GNN training orchestrator over all 7 trainers with
  `PYTHONPATH=.` + per-step time-box + skip-on-missing-dep (the existing `run_all.py` covered only
  3 classifiers). Syntax-checked and step-1-verified ✅.

### (c) Gaps found and how handled
- **No EMBEDDING/GDS install `.gsql` scripts exist** (no `ADD EMBEDDING`/HNSW/`Featurizer`/
  PageRank/Louvain DDL). Flagged in §6.4; native vectors/algorithms are code-driven
  (`app/ml/vector_client.py`, `app/ml/graph_algorithms.py`) with `VECTOR_CLIENT_MODE=local` as the
  working default and `scripts/check_tg_vector_support.sh` as the empirical probe. Did **not**
  invent scripts.
- **No combined launcher** → created `scripts/run_all.sh`.
- **`run_all.py` was a partial "train all"** (3 of 7 models) → created `scripts/train/run_all.sh`
  to cover all; kept `run_all.py` untouched.
- **Two TigerGraph layouts** (`docs/tigergraph_foundation/` vs repo-root `tigergraph/`) →
  documented the foundation package as authoritative (§6.3) and told the reader not to run both.
- **`uv` not installed in the codespace** → all `uv` lines tagged 🔶; verified the `python -m
  uvicorn` / `pip`-equivalent paths that the launcher falls back to.

### (d) Verified-in-codespace vs must-verify-live-on-client

**✅ Verified in codespace:** app import & boot (mock); all four health endpoints; 146-route count;
both dependency pre-check scripts (against public indexes); `train_revenue_decline` end-to-end incl.
anchor check; the two new scripts (`run_all.sh`, `train/run_all.sh`); ingestion endpoint presence.

**🔶 Must verify live on the client machine:** `uv venv` / `uv pip install` (uv absent here);
`smart_sdk` / `cdao*` install from the client artifactory; the dependency pre-checks against the
**client** artifactory URLs; TigerGraph connect / `CREATE SECRET` / schema+query install / live
loading (§6, §8-B); `check_tg_vector_support.sh` (needs the TG container); cdao PCL AWS login and
the real LLM/embedding health greens; the MCP Tier-1 checklist (`CLIENT_ENV_SETUP.md` §3b);
`env-health` all-green under real modes.
