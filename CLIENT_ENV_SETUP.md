# Client (JPMC) Environment Setup

How to bring this app up on the client machine, where the real TigerGraph, Azure OpenAI (via
SmartSDK/Fusion), and the internal PyPI artifactory are reachable — none of which are reachable
from the build box. Everything sensitive loads from `.env` (gitignored); this repo never commits
a real key, secret, token, or certificate.

Source of truth for the confirmed values: `SMARTSDK_REFERENCE.md` (verbatim client config).

---

## 0. The five environment swaps (adapter pattern, Section 2)

Nothing about the business/prompt/query logic changes between the build box and the client — only
these env selectors. All service code depends on the adapter *interfaces*, never the SDKs.

| Selector | Build box (here) | Client (JPMC) |
|----------|------------------|---------------|
| `GRAPH_CLIENT_MODE` | `mock` | `real` (live TigerGraph via pyTigerGraph/getToken) |
| `LLM_CLIENT_MODE` | `mock` / `claude` | `cdao_openai` (PRIMARY, cdao SDK) — fallback `azure` (SmartSDK/Fusion) |
| `EMBEDDING_CLIENT_MODE` | `local` (sentence-transformers) | `cdao_openai` (PRIMARY, cdao SDK) — fallback `azure` (SmartSDK) |
| `MODEL_CLIENT_MODE` | `deterministic` | `real` (if the ML deps + data are present) |
| `VECTOR_CLIENT_MODE` | `local` | `local` or `tigergraph` (once TigerVector confirmed) |

---

## 1. `.env` variables (copy `.env.example` → `.env`, fill the blanks)

Placeholders below are the confirmed client values; `<...>` are secrets to paste locally and
NEVER commit.

### Modes
```
GRAPH_CLIENT_MODE=real
LLM_CLIENT_MODE=cdao_openai       # PRIMARY (cdao SDK) — if it fails, fall back to azure (SmartSDK)
EMBEDDING_CLIENT_MODE=cdao_openai # PRIMARY (cdao SDK) — if it fails, fall back to azure (SmartSDK)
MODEL_CLIENT_MODE=real          # optional; falls back to deterministic if ML deps absent
```

### 1b. cdao OpenAI Azure client — the PRIMARY LLM **and embedding** path (`cdao_openai`)

Confirmed working by the developer in the client's Jupyter environment (simpler than the
SmartSDK path — try this FIRST for BOTH LLM and embeddings). One cdao install
(`cdaosdk-all[openai]`) and one PCL AWS login serve both adapters — they share the same
`openai_azure_client` construction (`build_cdao_openai_client` in `app/llm/client.py`).

**LLM** (`LLM_CLIENT_MODE=cdao_openai`) — verified pattern:
```python
from cdao import openai_azure_client
client = openai_azure_client(api_version="2024-02-01", workspace_id="906313")
client.chat.completions.create(model="gpt-4o-2024-08-06", messages=[...])
```
`CdaoOpenAILLMClient` (`app/llm/client.py`) wraps exactly this behind the standard `LLMClient`
interface — every agent/chat/insight path consumes it through `get_llm_client().generate()`
unchanged.

**Embeddings** (`EMBEDDING_CLIENT_MODE=cdao_openai`) — verified live (a real run returned a
3072-dim vector):
```python
response = client.embeddings.create(model="text-embedding-3-large-1", input=<text|list>)
vectors = [row.embedding for row in response.data]
```
`CdaoOpenAIEmbeddingClient` (`app/llm/embedding_client.py`) wraps exactly this behind the
standard `EmbeddingClient` interface — RAG ingestion and similarity consume it through
`get_embedding_client().embed()/embed_many()` unchanged.

**CRITICAL PREREQUISITE — PCL AWS login BEFORE starting the app (ONE login covers both
adapters).** The cdao client authenticates from the ambient AWS auth session established by the
PCL login; there are NO credentials in code or `.env` for it. Run the PCL AWS login in the same
shell/session, THEN start the backend. If the login has expired, cdao calls fail at request
time — re-run the login and restart.

**DIMENSION — CRITICAL.** `text-embedding-3-large-1` returns **3072-dim** vectors (vs local
sentence-transformers 384). When `EMBEDDING_CLIENT_MODE=cdao_openai`, `EMBEDDING_DIM` MUST be
set to `3072` so the TigerGraph `EMBEDDING` attribute DDL and the Chroma collection use the same
size — otherwise vector search silently breaks (see §5). The adapter raises loudly on a
dim mismatch rather than corrupting the vector space.

```
CDAO_API_VERSION=2024-02-01
CDAO_WORKSPACE_ID=906313          # workspace id from the client console (shared: LLM + embed)
CDAO_MODEL=gpt-4o-2024-08-06
CDAO_EMBEDDING_MODEL=text-embedding-3-large-1
EMBEDDING_DIM=3072                # REQUIRED for cdao text-embedding-3-large-1 (see §5)
```

Install (client artifactory only — see §2): `uv pip install -e ".[cdao]"` (pulls
`cdaosdk-all[openai]`, pinned to the `artifacts` index via `[tool.uv.sources]`) — this single
package covers both the LLM and embedding cdao adapters.

**If cdao_openai fails** (package unavailable, PCL/AWS session issues, workspace errors):
fall back to `LLM_CLIENT_MODE=azure` / `EMBEDDING_CLIENT_MODE=azure` (SmartSDK/Fusion below) —
same prompts/inputs, same interfaces, different transport. Selecting `cdao_openai` without the
package installed raises a clean `LLMClientError`/`EmbeddingClientError` naming the fix; it never
crashes the boot of other modes.

### SmartSDK / Fusion — Azure OpenAI LLM + Embeddings (`smart_sdk`) — SECONDARY alternate for
BOTH LLM (`LLM_CLIENT_MODE=azure`) and embeddings (`EMBEDDING_CLIENT_MODE=azure`), used only if
the PRIMARY cdao_openai path (§1b) is unavailable
```
AZURE_AUTH_METHOD=key           # key (primary, confirmed) | certificate (alternate)
AZURE_MODEL_NAME=gpt-4o-2024-08-06
AZURE_DEPLOYMENT_NAME=gpt-4o-2024-08-06
AZURE_API_KEY=<Azure/OpenAI tenant key from the client console>
AZURE_API_VERSION=2024-02-01
AZURE_ENDPOINT=https://llm-multitenancy-exp.jpmchase.net/ver2   # remove /ver2 in prod per console
FUSION_BASE_URL=https://llm-multitenancy-exp.jpmchase.net
FUSION_WORKSPACE_ID=<App Developer workspace id, e.g. 906313>
FUSION_ENV=prod
AZURE_EMBEDDING_MODEL_NAME=text-embedding-3-small
AZURE_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-small
EMBEDDING_DIM=1536              # text-embedding-3-small=1536 (-3-large=3072). See §5.
```
Certificate auth instead (`AZURE_AUTH_METHOD=certificate`):
```
AZURE_CERTIFICATE_PATH=/abs/path/agentbuilder.pem
AZURE_TENANT_ID=<...>
AZURE_CLIENT_ID=<...>
AZURE_API_KEY=<...>
```

### TigerGraph — real connection (`getToken(secret)`, SSL)
```
TG_HOST=https://wh-110ecdf498.svr.us.jpmchase.net
TG_GRAPHNAME=iperform_insights_coaching_demo
TG_USERNAME=R757680
TG_USE_SSL=true
TG_GS_PORT=14240
TG_SECRET=<paste the CREATE SECRET output — see §3>
```
Auth precedence in the pyTigerGraph tier: `TG_JWT_TOKEN → TG_API_TOKEN → TG_SECRET(getToken) →
user/pass`. With only `TG_SECRET` set, the client calls `conn.getToken(secret)` automatically —
this path already exists (`app/graph/tiered_client.py`) and fits the client config as-is.

### Anthropic (only if you also want `LLM_CLIENT_MODE=claude` for spot checks)
```
ANTHROPIC_API_KEY=<...>
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

---

## 2. Artifactory (`uv.toml`)

### 2.0 Dependency pre-check — run this FIRST, before any install

Two scripts verify every dependency against the client artifactory BEFORE anything is
installed, so missing libraries surface upfront rather than mid-build:

```
python scripts/check_client_deps.py    # all pyproject groups (core/dev/aws/ml/gds/cdao) + smart_sdk
python scripts/check_client_npm.py     # frontend/package.json deps + devDeps
```

- Defaults point at the client artifactory (PyPI:
  `…/artifactory/api/pypi/pypi/simple`; npm: `…/artifactory/api/npm/npm/`). Override with
  `--index-url` / `--registry` or `CLIENT_PYPI_INDEX` / `CLIENT_NPM_REGISTRY`.
- Each package is reported AVAILABLE (3.12-compatible version satisfying the pin) /
  VERSION-MISMATCH / MISSING; at-risk packages (torch, torch-geometric,
  sentence-transformers, chromadb, pyTigerGraph[gds], smart_sdk, cdaosdk-all) print their fallback from
  the table below when not cleanly available.
- Exit codes: 0 = pass, 1 = a required dep has an issue, 2 = index unreachable (clear
  message — if you're not on the client network, pass the public index to validate logic).

### 2.0b npm registry auth (`frontend/.npmrc`)

Copy the committed template to activate the client registry for npm (the template holds NO
token; the real `frontend/.npmrc` is gitignored):

```
cp frontend/.npmrc.client-template frontend/.npmrc
```

If `npm install` (or the pre-check) returns an auth/401 error, uncomment the
`always-auth=true` and `_authToken` lines in `frontend/.npmrc` and supply a token issued by
the artifactory — parallel to the TigerGraph secret in §3. Never commit the file with a token.

`uv.toml` is committed and points every dependency — including `smart_sdk`, which is not on public
PyPI — at the client index:
```toml
[[index]]
url = "https://artifacts-read.gkp.jpmchase.net/artifactory/api/pypi/pypi/simple"
default = true
```
Install:
```
uv pip install -e .            # core deps
uv pip install -e ".[cdao]"    # cdao SDK (cdaosdk-all[openai]) — PRIMARY LLM path (§1b)
uv pip install -e ".[ml,gds]"  # optional: real ML/GNN tier + pyTigerGraph[gds]
uv pip install smart_sdk       # client-only; secondary LLM path + embeddings; not in pyproject by design
```

### Library fallback table (when the artifactory is the sole index)

| Package | Risk | Fallback |
|---------|------|----------|
| `torch` / `torch-geometric` | large native wheels; CPU wheel/tag mismatch | install `torch` first from the artifactory torch channel, then matching `torch-geometric`. App runs without them — `app/ml/*` guard the imports and fall back to deterministic scorers. |
| `sentence-transformers` | pulls torch + model download | not needed at all when `EMBEDDING_CLIENT_MODE=azure`; otherwise pre-stage the model. |
| `chromadb` | needs `onnxruntime` for its default embedder (unused — we pass our own vectors) | pin `onnxruntime` if the default build is unavailable. |
| `pyTigerGraph[gds]` | `[gds]` extra adds torch/pandas GDS helpers | base `pyTigerGraph` still connects; GNN falls back to local PyG or deterministic projection. |
| `smart_sdk` | client-artifactory only | guarded import — absence never blocks boot in mock/claude/real mode. Required only for `azure` modes. |
| `cdaosdk-all[openai]` | client-artifactory only (pinned to the `artifacts` index via `[tool.uv.sources]`) | guarded import — one package serves the PRIMARY client LLM (`LLM_CLIENT_MODE=cdao_openai`) AND embedding (`EMBEDDING_CLIENT_MODE=cdao_openai`) paths; if unavailable, fall back to the `azure` (SmartSDK) modes for both. |

---

## 3. TigerGraph secret (`getToken`)

The developer has admin access. In GSQL (SMARTSDK_REFERENCE.md §7):
```
CREATE SECRET iperform_insights_coaching_demo
# → The secret: <SECRET_STRING> has been created for user "R757680".
```
Save `<SECRET_STRING>` into `.env` as `TG_SECRET` (TigerGraph cannot restore it). The app converts
it to a REST++ token via `getToken(secret)` on first connect. SSL is on (`TG_USE_SSL=true`).

---

## 3b. TigerGraph MCP tier — live verification checklist (client machine only)

The 4-tier GraphClient (`GRAPH_CLIENT_MODE=auto|tiered|mcp` → **MCP → pyTigerGraph → RESTPP →
Mock**, `app/graph/tiered_client.py`) was verified in the codespace as far as possible
(tier order, clean per-step fallback, cooldown, tier logging — see STATUS_CHECK.md Session 17
ITEM 8). What CANNOT be verified off the client network is Tier 1 actually *succeeding* against
the client's TigerGraph — that needs this checklist, run on the client machine.

**How Tier 1 works / what it needs:** the app spawns the official `tigergraph-mcp` server as a
local **stdio subprocess** (`app/graph/tigergraph_mcp_stdio_client.py`) — there is no separate
MCP server URL to configure. The subprocess receives the SAME `TG_*` env the pyTigerGraph tier
uses: `TG_HOST`, `TG_GRAPHNAME`, `TG_USERNAME`, `TG_PASSWORD` / `TG_API_TOKEN` / `TG_SECRET` /
`TG_JWT_TOKEN`, `TG_RESTPP_PORT`, `TG_GS_PORT`, `TG_SSL_PORT`, `TG_CERT_PATH` (all in
`.env.example` §"TigerGraph — Section-9.4 4-tier adapter"). So: one `.env`, all four tiers.

Steps (after §3's secret is in `.env` and `uv pip install -e .` has installed `tigergraph-mcp`):

1. Set `GRAPH_CLIENT_MODE=auto` in `.env`; start the backend.
2. **Confirm the MCP tier connects:** `curl -s localhost:8000/graph-access/health` (or open the
   Connection & Environment Health screen). In the tiered health payload, expect
   `"active_tier": 1, "active_tier_name": "tigergraph-mcp", tiers[0].healthy: true`.
   If tier 1 shows an error, the message is the real cause (auth, SSL, host) — fix per §3.
3. **Confirm agents use MCP FIRST:** load any data page (Advisor 360) or run
   `POST /agentic-ai/run`, then check the Admin/Data Health page's adapter-status panel
   (backed by `tier_status()`): `usage.served_by_tier` should count requests under tier `1`,
   and recent request rows should show `tier1 tigergraph-mcp ok=True`. Every served request
   also carries `served_by`/`served_by_tier` in its result envelope.
4. **Prove the fallback live:** make tier 1 fail (simplest: run once in a scratch venv without
   `tigergraph-mcp` installed; or temporarily rename the executable) and repeat step 3:
   requests must now log `tier2 pytigergraph ok=True` with `fallback_from` naming the tier-1
   error, no crash, and tier 1 on a 60s cooldown (`GRAPH_TIER_COOLDOWN_SECONDS`). Restore,
   wait out the cooldown (or restart), confirm tier 1 serves again.
5. **Reading the logs:** every dispatch is recorded in the TierUsageLog (Admin page +
   `tier_status()`): tier number/name, operation, target, latency ms, ok/error, and
   `fallback_from` listing exactly which higher tiers failed first. If a page shows data while
   `served_by_tier` is 4 (mock), the engine is unreachable — an unambiguous signal, never a
   silent degradation.

---

## 4. SmartSDK LangGraph import remapping

SmartSDK re-exports the LangGraph symbols; graph-construction signatures are unchanged — only
import paths differ. All native-LangGraph construction is isolated in ONE module:
**`app/agents/workflows/langgraph_builder.py`** (see its docstring for the full block). The swap:

```python
# native (this build)                     ->  SmartSDK (client)
from langgraph.graph import StateGraph, END
#   becomes:
from smart_sdk.ext.langgraph.graph.state import StateGraph
from smart_sdk.ext.langgraph import (ToolNode, InMemorySaver, END, ...)
from smart_sdk.ext.langgraph.adapter._adapter import LangGraphAgent
```
Notes: `ToolNode(core=...)` is deprecated → use `tools=`. Execution can move from
`.compile().invoke(...)` to `Runner(app_name, session_id).run_async(user_id, new_message)` for
telemetry/eval (SMARTSDK_REFERENCE.md §5) — optional; the plain invoke path works after the import
flip alone.

### LLM adapter internals (already built)
`AzureOpenAILLMClient` / `AzureOpenAIEmbeddingClient` (`app/llm/`) build a `smart_sdk.models.Model`
and convert via `_to_langgraph_model` (chat). **Embedding conversion:** the reference documents
`_to_langgraph_model` for chat only; the exact Model→embeddings symbol is not in the reference.
`AzureOpenAIEmbeddingClient._resolve_embedder` tries the known candidates and raises a precise
error if none match — if your SmartSDK build names it differently, add it there (the one
client-side confirmation point). The `Model(...)` construction itself is confirmed and complete.

---

## 5. Embedding dimension consistency

`EMBEDDING_DIM` must match: the active embedding adapter's output, the TigerGraph `EMBEDDING`
attribute DDL (`EMBEDDING(DIMENSION=EMBEDDING_DIM, METRIC="COSINE")`), and the Chroma collection.
Per active mode: `local` sentence-transformers = **384**; `cdao_openai` text-embedding-3-large-1
= **3072** (PRIMARY client path); `azure`/`azure_openai` text-embedding-3-small = **1536**,
-3-large = **3072**.
- Switching modes (e.g. `local` 384 → `cdao_openai` 3072): set `EMBEDDING_DIM` accordingly **and
  rebuild the Chroma collection** (a fixed-dim collection cannot accept differently-sized vectors)
  — re-run `scripts/ingest_sample_knowledge.py`. The embedding client raises loudly on a dim
  mismatch rather than silently corrupting the vector space.

---

## 6. First-run checklist (client machine)

1. **Dependency pre-check (§2.0) — before anything else:**
   `python scripts/check_client_deps.py` and `python scripts/check_client_npm.py` against the
   artifactory. Resolve every MISSING/VERSION-MISMATCH per the §2 fallback table first.
2. `git clone` the repo; `cp .env.example .env`.
3. Fill `.env` per §1 (modes + SmartSDK/Fusion + TigerGraph). Paste `TG_SECRET` from §3.
4. Ensure `uv.toml` is present (it is committed). `uv pip install -e ".[cdao,ml,gds]"` then
   `uv pip install smart_sdk`. Frontend: `cp frontend/.npmrc.client-template frontend/.npmrc`
   (§2.0b) then `npm install` in `frontend/`.
5. **Run the PCL AWS login** (required by the cdao LLM + embedding clients, §1b — one login
   covers both) in the shell that will run the backend — cdao has no credentials in `.env`; it
   uses this ambient session.
6. TigerGraph: `CREATE SECRET` (§3); install schema/queries and load the 192 manifest CSVs from
   `docs/tigergraph_foundation/` (see `CLAUDE.md` §8 / `scripts/install_tigergraph_source_of_truth.sh`;
   the app's Data Ingestion & Sync page "Run All Ingestion" loads the complete graph remotely).
7. Boot check (mock first, to isolate app issues from connectivity):
   `GRAPH_CLIENT_MODE=mock LLM_CLIENT_MODE=mock uvicorn app.api.main:app` → confirm it serves.
8. Flip to real: set the §1 modes, restart, and open the **Connection & Environment Health**
   screen (built for exactly this) to confirm TigerGraph auth/SSL/graph/counts, LLM test
   generation, embedding dimension, and Chroma — each green/red with the real error if red.
9. If any tier is red, the health screen shows the real error; fix per the fallback table (§2)
   and re-check. Do not proceed to demo until all green.

---

## 7. Security invariants (do not violate)

- No real key / secret / token / certificate path with a real value is ever committed. `.env` and
  `.env.*` are gitignored; only `.env.example` (placeholders) is tracked.
- SDK imports (`smart_sdk`, `openai`, `anthropic`, `pyTigerGraph`) live only inside their adapter
  classes — never at module top-level elsewhere — so a missing client-only package never blocks
  boot in another mode.
