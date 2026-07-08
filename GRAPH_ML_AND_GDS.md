# Graph ML & TigerGraph GDS — Current State + Client-Environment Native Conversion Plan

**Why this doc exists:** to be precise about what actually runs where, so nobody (you, the client,
or a future maintainer/Copilot) is confused about what is "TigerGraph-native" vs. "Python compute
with TigerGraph as the data store." The results are all REAL either way — this is about WHERE the
compute happens, which affects the architecture story and scale.

---

## PART 1 — CURRENT STATE (honest inventory)

### What genuinely runs INSIDE TigerGraph (native graph engine work)
- **Multi-hop graph traversal reasoning** — real GSQL traversal queries (GQ-###) executed in
  TigerGraph: advisor → households → outcomes → similar advisors, etc. This is genuine
  TigerGraph graph work and is the backbone of the agentic graph-reasoning feature.
- **Entity/relationship storage** — the temporal knowledge graph (60 vertices / 132 edges /
  156,247 rows) is the source of truth.
- **Vector storage (conditional)** — `app/ml/vector_client.py` with `VECTOR_CLIENT_MODE=tigergraph`
  will issue native EMBEDDING/HNSW GSQL *at runtime only if the instance supports it*; the DEFAULT
  is `local`. So native vector storage is available-but-not-default.

### What runs in PYTHON (TigerGraph is the data source/store, NOT the compute engine)
- **Classical graph algorithms** — `app/ml/graph_algorithms.py` computes PageRank (referral-network
  centrality) and Louvain (AGP cohort/community detection) using **networkx**, NOT TigerGraph's
  native GDS library. There are NO GDS `.gsql` scripts installed.
- **GraphSAGE GNN** — `scripts/train/train_graphsage_embeddings.py` trains GraphSAGE via **PyTorch
  Geometric (torch-geometric)** to learn node embeddings. Current path is local PyG on graph data
  pulled into Python (with a deterministic-projection fallback if torch-geometric is absent). It is
  real GraphSAGE, but it does NOT use `pyTigerGraph[gds]`'s native `neighborLoader` /
  `GraphSAGEForVertexClassification` (the "TigerGraph-native GNN" path).
- **Sequence forecast (GRU/LSTM)** — a time-series ML model for revenue forecasting. Not a graph
  algorithm at all; standard PyTorch.
- **Tabular models** — RandomForest/XGBoost (revenue-decline risk, AGP off-track, household churn),
  SHAP contributions. Standard scikit-learn/XGBoost in Python.
- **Anomaly detection** — Isolation Forest (Python).

### The accurate one-line story for the client
- ✅ TRUE: "TigerGraph is our temporal knowledge graph — it stores all entities/relationships and
  performs real multi-hop graph-traversal reasoning."
- ✅ TRUE: "We run a GraphSAGE GNN for embeddings, XGBoost for predictions, a GRU for forecasting,
  Isolation Forest for anomaly detection — real ML on real data."
- ⚠️ OVERSTATED if claimed today: "We use TigerGraph's NATIVE GDS graph algorithms and NATIVE GNN
  training." Today the algorithms and GNN run in Python with TigerGraph as the data source. See
  Part 2 to make this true on the client machine.

### Why it's this way (not a defect)
The codespace has **no live TigerGraph** reachable — so the native `pyTigerGraph[gds]` neighborLoader
(which pulls neighborhoods from a live instance) and native GDS algorithm installs literally cannot
run or be tested here. Python-based compute was the only path that could be built and verified in the
codespace. Converting to native is inherently a **client-environment task**, to be done against the
real TigerGraph 4.2.2 instance. `pyTigerGraph[gds]` is present in pyproject as an OPTIONAL dependency
in anticipation of this conversion — but nothing uses its native GDS/GNN path yet (see the pyproject
note; the extra is commented/flagged to avoid implying it's active).

---

## PART 2 — CONVERT TO NATIVE TigerGraph GDS + GNN ON THE CLIENT MACHINE (step by step)

Do this on the client machine, against the live TigerGraph 4.2.2 instance, AFTER the base setup
runbook is complete (schema installed, data loaded, connectivity green). Each step is optional/
incremental — the app works with the Python path if you stop here; this makes it TigerGraph-native.

### Prerequisites
- Base setup complete (CLIENT_SETUP_RUNBOOK.md phases 1–5): schema + data loaded, health green.
- `pyTigerGraph[gds]` installed from the client artifactory (uncomment it in pyproject / install the
  `gds` extra). Confirm `torch` + `torch-geometric` are available from the artifactory (the
  dependency pre-check flags these as at-risk).
- Confirm the live instance supports GDS + vector: run `scripts/check_tg_vector_support.sh` and
  probe whether the GDS library installs (TigerGraph 4.2.2 supports both, but confirm on the actual
  instance/edition).

### Step A — Install TigerGraph's native GDS algorithm library
- Install TigerGraph's Graph Data Science functions so PageRank/Louvain/centrality/similarity run
  IN-DATABASE. Via `pyTigerGraph`: `conn.gds` / `Featurizer.installAlgorithm(...)`, or install the
  GDS GSQL queries directly. (These are TigerGraph's own algorithm queries, installed like your
  GQ-### queries.)
- CHECK: `Featurizer.listAlgorithms()` (or GraphStudio) shows the installed algorithms; a test run
  of PageRank returns scores.

### Step B — Repoint classical algorithms from networkx → native GDS
- In `app/ml/graph_algorithms.py`, add a `mode` (e.g. `GRAPH_ALGO_MODE=tigergraph|networkx`,
  default networkx as fallback): when `tigergraph`, call the installed native GDS PageRank/Louvain
  via `pyTigerGraph` instead of computing in networkx. Keep networkx as the guarded fallback.
- CHECK: referral-network centrality + AGP cohort features now come from native GDS; results are
  consistent with (or better than) the networkx version; the app's centrality/cohort UI is unchanged.

### Step C — Native EMBEDDING attributes + HNSW vector index
- Apply `ALTER VERTEX <type> ADD EMBEDDING ATTRIBUTE <name> (DIMENSION=3072, INDEX=HNSW,
  DATATYPE=FLOAT, METRIC=COSINE)` for the entities that carry GNN embeddings. (These DDL scripts do
  NOT exist in the repo today — create them under docs/tigergraph_foundation/tigergraph/schema/ as a
  new file, e.g. `04_embeddings.gsql`, OR generate via `app/ml/vector_client.py` `tigergraph` mode.)
  DIMENSION MUST equal `EMBEDDING_DIM`=3072 (the cdao text-embedding-3-large model).
- Set `VECTOR_CLIENT_MODE=tigergraph` so vectors are stored/searched natively (HNSW) instead of the
  local store.
- CHECK: EMBEDDING attributes exist with dim 3072; a native vector-similarity GSQL query returns
  nearest neighbors; the similarity/peer-benchmark features read from native vector search.

### Step D — Native GraphSAGE via pyTigerGraph[gds] neighborLoader
- In `scripts/train/train_graphsage_embeddings.py`, add a `tigergraph` training path that uses
  `pyTigerGraph`'s `neighborLoader()` to sample neighborhoods directly from the live graph into
  PyTorch Geometric (instead of building the in-memory graph in Python), and/or TigerGraph's
  `GraphSAGEForVertexClassification`. Keep the local-PyG path as fallback.
- Write the learned embeddings BACK into the native EMBEDDING attributes (Step C).
- CHECK: training runs pulling neighborhoods from the live instance; embeddings land in the graph's
  EMBEDDING attributes; the Embeddings page + similarity features reflect the native GNN output.

### Step E — Verify the "native" story end to end
- Confirm: classical algorithms run in-database (GDS), embeddings stored + searched natively (HNSW),
  GraphSAGE trained via TigerGraph's neighborLoader. Now the claim "we use TigerGraph's native GDS
  and native GNN" is TRUE.
- CHECK: env-health / a short verification script confirms each native path is active; results match
  the anchored figures.

### If any step can't be completed (dependency/instance limitation)
- Each step has a Python fallback already in place — the app keeps working. Document which native
  steps succeeded vs. which fell back, so the architecture claims stay accurate to reality.

---

## PART 3 — SUMMARY FOR THE DEMO
- Be precise: "TigerGraph stores the graph and does real multi-hop traversal reasoning; our GNN/ML
  runs in Python today, with a documented path to native TigerGraph GDS/GNN in the target
  environment." That's an honest, strong, and defensible position — and Part 2 is the concrete plan
  to make it fully native on the client's real instance.

---

## PART 4 — COPILOT WORKING NOTES (read before doing the Part 2 conversion with Copilot)

**How to use Copilot for this conversion — realistic model:**
Copilot is a co-pilot here, not an autopilot. It can write the code, but it CANNOT test against the
live TigerGraph — you run each step on the real instance, hit an error, paste it to Copilot for a
fix, re-run. The doc's Steps A–E are already broken into concrete, file-specific tasks to make that
loop efficient. You can ALSO bring harder problems back to Claude (chat) between Copilot sessions —
you're not limited to Copilot in the client environment.

**Where Copilot is likely to be WRONG (verify these against real docs, don't trust blindly):**
- `pyTigerGraph[gds]`'s native API (`neighborLoader`, `Featurizer.installAlgorithm` /
  `runAlgorithm`, `GraphSAGEForVertexClassification`) is specialized and under-represented in
  Copilot's training data — it may hallucinate method names or argument shapes. Verify every
  `pyTigerGraph` GDS call against the official pyTigerGraph GDS documentation or the installed
  package's source.
- GSQL (for the EMBEDDING DDL and any GDS query installs) is a niche language — Copilot is weaker
  here than in Python. Check GSQL syntax against TigerGraph 4.2.2's actual docs.

**Confirmed-correct native EMBEDDING DDL syntax** (from TigerGraph's own docs/research — use this as
the reference for Step C rather than a Copilot guess):
```gsql
ALTER VERTEX Advisor
  ADD EMBEDDING ATTRIBUTE profile_emb (
    DIMENSION = 3072,        -- MUST match EMBEDDING_DIM / cdao text-embedding-3-large
    INDEX = HNSW,
    DATATYPE = FLOAT,
    METRIC = COSINE
  );
```
(Repeat per vertex type that carries GNN embeddings. Native vector search then composes with graph
traversal in one GSQL query — "similar to X AND connected to Y".)

**Suggested Copilot workflow per step:**
1. Open the target file named in the step (e.g. `app/ml/graph_algorithms.py`).
2. Ask Copilot to add the `tigergraph` mode alongside the existing implementation, KEEPING the
   Python path as a guarded fallback (never rip out the working fallback).
3. Run it against the live instance; if it errors, paste the real error to Copilot (or to Claude
   chat for harder reasoning).
4. Verify the step's CHECK passes before moving to the next step.
5. Update GRAPH_ML_AND_GDS.md / STATUS notes with which native steps succeeded vs. fell back, so the
   architecture claims stay accurate to reality.

**Golden rule:** every native step must keep its Python fallback working, and you only claim
"TigerGraph-native" for the steps that actually verified live. Honesty over impression.
