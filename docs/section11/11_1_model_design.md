# Section 11.1 Design — Real Model Tier (`ModelClient` adapter)

_Fable-architect design document, 2026-07-05. Design only — the main thread implements,
commit-by-commit, per the sequence in §12. Every claim below was grounded against the real repo
and real data on this machine; citations are `file:line` or real command output._

---

## 0. Verified current state (what this design builds on — checked, not remembered)

| Fact | Evidence |
|---|---|
| Live `/predictions` path is the additive scorecard | `app/api/routers/predictions.py:3,11,16,21` → `app.prediction.service.PredictionService`; agent tool `app/agents/tools/service_tools.py:36-37` uses the same class. |
| Dormant RF exists, trained on a synthetic rank-heuristic | `app/prediction/prediction_engine.py:33-54` (`_synthetic_target`), only caller `app/services/prediction_service.py:13` — no router/agent imports it (grep confirmed). |
| Scorecard already advertises the trained alternative | `app/prediction/service.py:56` `"trained_alternative": "scikit-learn RandomForest (used when per-cohort training data is sufficient)"`. |
| Contribution shape the UI consumes | `{feature, value, points, why}` — produced at `app/prediction/service.py:77-80`, rendered as relative bars at `frontend/components/predictions/prediction-workspace.tsx:127-129` (bars scale by max `points`; points are non-negative today). |
| Adapter house style to copy | `Protocol` + local-SDK-imports-inside-implementation + cached `get_*_client()` factory + `reset_*()`: `app/llm/client.py:13-155`, `app/llm/embedding_client.py:12-109`, `app/graph/client.py:36-345`. |
| 33 Feature_Catalog features (advisor-level) | Enumerated in `app/features/engineering.py:76-231` (revenue_ltm … time_sensitivity_score; counted = 33). |
| Deterministic embedding today | `app/embeddings/service.py:15-52`: `deterministic-feature-projection`, dim 8, over 16 `PROJECTION_FEATURES`; persisted to SQLite; `app/embeddings/similar_entities.py` does cosine over `phx_dm_embedding.vector_preview`. |
| STALE module, do not extend | `app/embeddings/graph_builder.py:10` reads `tigergraph/sample_data` (pre-foundation path that no longer matches the data package). Replace, don't reuse. |
| In-memory graph source for PyG | `MockGraphClient`/`FoundationGraphStore` exposes `store.vertices`, `store.edges`, `store.out_index`, `store.in_index` (`app/graph/client.py:279-300`). |
| Data volumes (real `wc -l`/CSV scans) | 60 advisors; 360 households (all `ACTIVE`; HNW 203 / AFFLUENT 157); 720 accounts (all `ACTIVE`); 15,116 revenue transactions **2023-08-01 → 2026-07-28**; `transaction_for_household` edges 15,116; monthly AUM/NNM/NCF 2,160 rows each (60 × 36 months, 2023-08-31 → 2026-07-31); `phx_dm_agp_kpi_measurement` 960 rows, **all measured_at 2026-07-01** (single snapshot), status OFF_TRACK 614 / ON_TRACK 346. |
| Empirical label prevalence (computed on real data, script in §3) | 6 quarterly cut points × 360 households, activity floor $500 → **n = 2,159** samples. 15 %-decline label: **26.6 % positive**. 30 %-drop label: **3.8 % positive (83)**. Zero-transaction 3m/6m windows: **0.0 %** (generator gives every household continuous activity — "went silent" labels are impossible on this data). |
| Libraries (definitive import check) | `sklearn 1.9.0`, `xgboost 3.3.0` ✅, `shap 0.52.0` ✅, `numba 0.66.0` ✅, `torch 2.12.1+cpu` ✅, `networkx 3.6.1` ✅, `pyTigerGraph 2.0.4` ✅ (`Featurizer` imports OK; its built-in `GraphSAGEForVertexClassification` raises "PyTorch Geometric required"), `chromadb 1.5.9`. **Missing: `torch_geometric`** (pip dry-run resolves `torch-geometric 2.8.0` pure-Python wheel — trivial install), `lightgbm` (not needed). |
| TigerGraph container | `tigergraph/community:latest`, container exists, currently **Exited** (`docker ps -a`). Any live-TG check requires starting it; live query INSTALL has repeatedly failed on this 2-core box (Phase 2/3 finding). |
| Admin page extension point | `frontend/app/(dashboard)/admin/page.tsx` → `AdminHealthWorkspace` (`frontend/components/admin/admin-health-workspace.tsx`, 136 lines, no Tabs yet). |
| Anchored figures (read-only guardrail) | A001 revenue_ltm 387,293.22 / aum 10,018,200 / nnm_3m 102,080 / kpi 0.275; A020 539,262.90 / 25,990,000; F001 38,365,750.01. |

**Installs required (exactly):** `pip install torch-geometric` (one package; wheel confirmed
resolvable). Nothing else — xgboost and shap are already present despite an earlier anomalous
import failure (re-verified twice; treat the first check as transient).

---

## 1. `ModelClient` adapter

New package **`app/ml/`** (avoid `app/models/` — that's the pydantic package). Mirror
`app/llm/client.py` exactly: `Protocol`, error class, implementations with heavy imports inside
`__init__`/methods only, cached `get_model_client()`, `reset_model_client()`.

```python
# app/ml/client.py  (NO sklearn/xgboost/torch/shap imports at module top level)
class ModelClientError(RuntimeError): ...
class ModelUnavailableError(ModelClientError):
    """Raised when the real tier has no adequate trained artifact for this request.
    Callers MUST catch this and fall back to the deterministic scorer."""

class ModelScore(TypedDict):
    score: float                # 0-100, same scale as scorecard
    confidence: float           # 0-1
    contributions: list[dict]   # {feature, value, points, why, direction} — §4
    served_by: str              # e.g. "xgboost-revenue-decline-v1" | "scorecard"
    model_card_ref: str         # registry key
    methodology_patch: dict     # merged into the scorecard's methodology dict

class ModelClient(Protocol):
    def score_risk(self, prediction_type: str, entity_type: str, entity_id: str,
                   features: dict) -> ModelScore: ...
    def forecast_series(self, entity_type: str, entity_id: str,
                        series: list[dict], horizon: int = 6) -> dict: ...   # §5 contract
    def anomaly_scores(self, entity_type: str, rows: list[dict]) -> list[dict]: ...  # §9
    def entity_embedding(self, entity_type: str, entity_id: str) -> list[float] | None: ...  # §7
    def describe(self) -> dict: ...
```

- **`DeterministicModelClient`** — thin delegation to the CURRENT verified code paths, which are
  **never deleted**: `score_risk` raises `ModelUnavailableError` unconditionally (so
  `PredictionService` runs its existing inline scorecard unchanged — see precedence in §2);
  `forecast_series` returns a labeled seasonal-naive projection (real arithmetic on real history,
  clearly `served_by: "seasonal-naive-baseline"`); `anomaly_scores` returns empty (feature not
  claimed in deterministic mode); `entity_embedding` reads the existing
  deterministic-feature-projection vectors (`app/embeddings/service.py`).
- **`RealModelClient`** — lazily loads artifacts from `models/artifacts/` via the registry (§10).
  All of `xgboost`, `shap`, `torch` are imported inside methods. If an artifact is missing,
  fails schema validation, or the registry entry's quality gate fails (§2), raise
  `ModelUnavailableError` — the caller's fallback IS the deterministic scorer, so real mode can
  never be worse than today.
- **Factory/env:** `MODEL_CLIENT_MODE=deterministic|real`, default `deterministic` in
  `.env.example` (add alias field in `app/config/settings.py` beside `graph_client_mode`,
  line 18). Cached singleton + `reset_model_client()`, same as `app/llm/client.py:133-155`.
- **Import rule (hard):** business code imports only `app.ml.client`. `grep -rn "import xgboost\|import shap\|import torch" app/ --include=*.py` must hit only `app/ml/real_*.py`, `app/ml/training/`, and the existing `sentence_transformers`-guarded embedding client.

---

## 2. Promoting the trained model to the live path

**Do not add a new endpoint.** `PredictionService.predict_revenue_decline` /
`predict_agp_off_track` (`app/prediction/service.py:72,124`) each gain one block before the
inline scorecard math:

```python
try:
    ms = get_model_client().score_risk("REVENUE_DECLINE_RISK", "ADVISOR", advisor_id, f)
    score, contributions, served_by = ms["score"], ms["contributions"], ms["served_by"]
    methodology = {**self._methodology(...), **ms["methodology_patch"], "served_by": served_by}
except ModelUnavailableError as exc:
    ...existing scorecard code, unchanged, methodology["served_by"] = "scorecard",
       methodology["fallback_reason"] = str(exc)
```

Everything downstream — result dict shape, `_persist` (`service.py:182-216`), reasoning trace,
frontend — is untouched, because `ModelScore.contributions` uses the exact
`{feature, value, points, why}` shape (plus an additive `direction` field, §4).

**Precedence rule (makes `service.py:56`'s promise real):** the real tier serves a prediction
type iff its registry entry says (a) artifact present, (b) held-out primary metric ≥ floor
(REVENUE_DECLINE ROC-AUC ≥ 0.65; AGP ROC-AUC ≥ 0.65; churn PR-AUC ≥ 3× base rate), (c) ≥ 80 %
of the model's feature list is non-null for this request. Otherwise
`ModelUnavailableError("insufficient per-cohort training data / coverage")` → scorecard. This is
literally "used when per-cohort training data is sufficient", now enforced in code, and the
served path is visible in every persisted methodology.

**Algorithm recommendation: XGBoost (`XGBClassifier`), replacing the dormant RandomForest.**
Reasons: native missing-value handling (feature snapshots have real `None`s, e.g.
`kpi_on_track_ratio` for non-enrolled advisors); exact TreeSHAP support in the installed `shap
0.52.0` (and `pred_contribs=True` natively in xgboost as a dependency-free cross-check);
`tree_method="hist", n_jobs=2` is trivial on this CPU. Baseline config for all three classifiers:
`n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
random_state=42` (+ `scale_pos_weight` for churn).

**Retire the dormant duplicate** (Section 0B policy — no "just in case" duplicates): after the
real path is live and verified, delete `app/services/prediction_service.py` and gut
`app/prediction/prediction_engine.py`'s `_synthetic_target` training (the file's last useful act
is the before/after comparison in §4 — run that first, then delete). Keep
`app/models/predictions.py` enums only if something else imports them (re-grep at implementation
time). Record the deletion + reasoning in PROGRESS.md.

---

## 3. Real-label training (the core of 11.1)

**Level:** household × as-of-date, per the honest small-data rule (60 advisors is not a training
set; 2,159 household-cut samples is). Advisor-level scores are **aggregations of household
predictions**, never a 60-row training run.

**Sample frame (verified empirically — the prevalence numbers in §0 came from running exactly
this):** as-of cut points `2024-08, 2024-11, 2025-02, 2025-05, 2025-08, 2025-11` (each leaves a
full 6-month label window ≤ 2026-07 and ≥ 12 months of history before it). A (household, cut)
row is included iff prior-6m revenue ≥ $500 (noise floor). Household monthly revenue = sum of
`phx_dm_revenue_transaction.revenue_amount` joined through `edges/phx_dm_transaction_for_household.csv`,
month-bucketed by `transaction_date` — read via `FoundationGraphStore`, or directly from the CSVs
in `docs/tigergraph_foundation/data/sample/` for the training scripts (read-only either way).

### 3.1 Label definitions (exact)

| Model | Unit | Label = 1 iff | Measured prevalence |
|---|---|---|---|
| **REVENUE_DECLINE_RISK** | household × cut | `revenue(t, t+6m] < 0.85 × revenue(t−6m, t]` (≥15 % decline over the next 6 months vs the trailing 6) | 26.6 % of 2,159 |
| **HOUSEHOLD_CHURN_PROPENSITY** (new) | household × cut | `revenue(t, t+6m] < 0.70 × revenue(t−6m, t]` (severe ≥30 % attrition — the strongest churn proxy this data supports; literal churn/zero-activity never occurs, verified) | 3.8 % (83 positives) |
| **AGP_OFF_TRACK_RISK** | KPI measurement (960 rows) | `status == "OFF_TRACK"` (single 2026-07-01 snapshot — a temporal label is impossible here; the model learns which *business behaviors* co-occur with off-track KPIs) | 64.0 % |

Churn honesty: the card must say "churn proxy = severe revenue attrition; this demo dataset
contains no household departures, so true attrition labels do not exist." Use
`scale_pos_weight ≈ 25` and report PR-AUC as primary.

### 3.2 Features (INPUT — distinct from embeddings, which are GNN OUTPUT, §7)

Household-level features, all computed **from raw facts ≤ cut date t only**:
trailing 3m/6m/12m revenue; revenue slope over last 6 monthly buckets (OLS); revenue volatility
(std of last 12 monthly buckets); months-since-peak-revenue; tx count 3m/6m; mean & max tx size
6m vs own 12m median (ratio); product count + 1−HHI diversification via
`transaction_for_product`; account count (`household_owns_account`); `total_aum`, `segment`,
`risk_profile`, `state` (one-hot); days since last transaction. Where a Feature_Catalog concept
applies at household level (diversification, activity recency), reuse the same formula as
`app/features/engineering.py:108-112,155-165` so the two layers tell one story.

AGP model features (advisor+KPI level): the advisor's Feature_Catalog behavioral features
(revenue_growth_3m_pct, ncf_3m, nnm_3m, pipeline, overdue_followup_count,
days_since_last_client_activity, lead/referral rates, tenure_months, milestone_days_remaining)
plus KPI metadata (kpi type one-hot, target_value) — see exclusion list below.

### 3.3 Anti-leakage rules (exact, enforced in code)

1. **Temporal wall:** every feature uses data with date ≤ t; every label uses (t, t+6m] only.
   Enforce with an assertion in the dataset builder: rebuild features with all rows > t deleted
   from the frame and assert bit-identical feature values.
2. **No label-derivative features:** for the two revenue models, **exclude any feature that is a
   deterministic function of the label windows** — specifically do NOT include "next-window"
   anything, and do not include `revenue_at_risk_estimate`-style derived features whose formula
   embeds the label's own decline term. Trailing revenue/trend features are legitimate (they are
   ≤ t).
3. **AGP exclusions (the sharp one — `status` is computed FROM `attainment_pct`):** exclude
   `attainment_pct`, `actual_value`, and the snapshot features that are direct derivatives of
   attainment: `milestone_attainment_pct`, `kpi_on_track_ratio`, `agp_risk_score`
   (`engineering.py:174-184`). `milestone_days_remaining` stays (time, not attainment).
4. **Leakage tripwire:** if held-out ROC-AUC > 0.97 for any model, the training script prints a
   `LEAKAGE SUSPECTED` banner and the registry entry is marked `quality_gate: failed` (blocks
   live serving) until reviewed. An honest 0.70 beats a leaked 0.99.

### 3.4 Splits and metrics (printed by every training script — real numbers, never asserted)

- Revenue-decline & churn: **temporal split** — train on cuts 2024-08…2025-05, test on 2025-08
  & 2025-11 (~720 test rows). Print: n_train/n_test, base rate, ROC-AUC, PR-AUC, Brier,
  precision@top-decile, and a 5-bin calibration table.
- AGP: single timestamp → **GroupShuffleSplit by advisor** (80/20, seed 42) so no advisor spans
  both sides. Print the same metrics.
- Every model card carries the small-data caveat verbatim: "Demo-scale synthetic-seeded data;
  n≈2.2K household-period samples from 360 households / 60 advisors; metrics indicate the
  pipeline is real, not production accuracy."

### 3.5 Advisor-level aggregation (what the live endpoint returns)

`REVENUE_DECLINE_RISK(advisor) = 100 × Σ_h w_h·P(decline_h) / Σ_h w_h`, weights `w_h` =
household trailing-6m revenue (a book-revenue-at-risk interpretation, matching the scorecard's
0–100 scale). Contributions = revenue-weighted mean of per-household SHAP values per feature
(§4). AGP: advisor score = 100 × mean predicted off-track probability over that advisor's KPI
measurement rows. Churn is surfaced per household (Advisor 360 / Client 360 household tables),
not aggregated into a fake advisor number.

### 3.6 Anchored-figures guardrail (hard)

Training reads CSVs / `FoundationGraphStore` only and **never calls `upsert`**. Each training
script ends by recomputing A001's snapshot through the normal path and asserting
`revenue_ltm == 387293.22`, `aum_total == 10018200`, `nnm_3m == 102080` — a cheap tripwire that
fails loudly if anything mutated shared state.

---

## 4. Real SHAP contributions

- `shap 0.52.0` installed (verified). Use `shap.TreeExplainer(model)` on the XGBoost boosters;
  cross-check once against `booster.predict(dmatrix, pred_contribs=True)` (native TreeSHAP,
  zero-dependency) — they must agree to ~1e-6, and the cheaper native path may serve at runtime.
- **Shape mapping (keeps `prediction-workspace.tsx:127-129` working unmodified):** for each
  feature, `points = round(|φ_i| × 100, 1)` (probability-space SHAP → 0-100 score scale),
  `direction = +1 if φ_i > 0 else -1` (new additive field), `why` text states direction
  explicitly ("raises risk by 6.3 points" / "reduces risk by 2.1 points"). Top 8 features by
  |φ|; remainder folded into `{"feature": "other_features", ...}` so bars stay readable.
- `methodology_patch` adds: `base_value` (expected score), the additivity identity
  `score ≈ base_value + Σ signed_points`, model name/version, and the registry key — the
  Predictions page's "how was this derived" section (Section 9.5) gets strictly deeper, not
  different.
- **Before/after verification (scripted, committed as `scripts/verify_contributions.py`):**
  1. `MODEL_CLIENT_MODE=deterministic` → capture A001's live scorecard contributions (today's
     behavior, the "before" for the endpoint).
  2. One final run of the dormant engine with `_synthetic_target` on the same feature matrix →
     SHAP values for A001 (the "before" for the *model*, per 11.1's "synthetic-label model").
  3. `MODEL_CLIENT_MODE=real` → live endpoint again → real-label SHAP contributions.
  Print a three-column table (feature | synthetic-label SHAP | real-label SHAP | scorecard
  points) for A001 and one more advisor; assert the response JSON schema is unchanged; save the
  raw outputs to `docs/section11/evidence/contributions_before_after.json`. Then delete the
  dormant path (§2).

---

## 5. Sequence model — revenue forecast with uncertainty band

- **Data:** 60 advisor series × 36 months (monthly revenue = per-advisor monthly transaction sum,
  consistent with `_revenue_summary`, `engineering.py:65`; `phx_dm_monthly_*` confirmed 60×36).
- **Architecture (one shared model, not 60):** GRU, 1 layer, hidden 32, input per step =
  `[z-scored log1p(revenue) (per-advisor normalization), sin(2πm/12), cos(2πm/12)]`, linear head
  → next-month value. Train next-step on months 1–30 of every series; validate on 31–36.
  ~15K params — seconds per epoch on 2 cores.
- **Time-box:** max 200 epochs, early-stop patience 20, hard wall-clock cap 5 min
  (`--max-minutes` flag); reduction fallback hidden 16 / seq-sampled batches, reduction recorded
  in the model card. Never retrain on boot — artifact `models/artifacts/revenue_gru_v1.pt`.
- **Forecast:** 6-month autoregressive rollout per advisor. **Uncertainty band = empirical
  validation-residual quantiles** (per-horizon-step residual distribution → p10/p90; honest and
  simple; MC-dropout at this scale would be decoration).
- **Mandatory baselines, printed:** seasonal-naive (same month last year) and 3-month moving
  average; report sMAPE for GRU vs both on the validation months. If the GRU does not beat
  seasonal-naive, the card says so and `served_by` names whichever is better —
  `DeterministicModelClient.forecast_series` already returns seasonal-naive, so the fallback is
  free.
- **Output contract** (new `GET /predictions/forecast/{advisor_id}` + reused by Revenue pages):

```json
{"entity_id":"A001","granularity":"month",
 "history":[{"month":"2026-06","actual":31240.5}],
 "forecast":[{"month":"2026-08","p50":30110.0,"p10":26400.0,"p90":34100.0}],
 "model":{"served_by":"gru-revenue-forecast-v1","val_smape":0.14,
          "baseline_smape":{"seasonal_naive":0.19,"ma3":0.22},
          "caveats":["60 series × 36 months — demo scale"]}}
```

Frontend: Recharts `Line` (p50) + `Area` (p10–p90) appended after the history line, dashed,
"Forecast" chip using the existing AI-accent token — visualization-fidelity rule applies.

---

## 6. Classical graph algorithms — deterministic-first, TG-GDS documented fallback

**Hard constraint honored:** nothing here requires live query INSTALL. The deterministic-mode
implementation is **networkx (3.6.1, installed) over a `FoundationGraphStore`-built graph** —
a new `app/ml/graph_algorithms.py` with a builder that reads `store.vertices`/`store.edges`
(replacing the stale `app/embeddings/graph_builder.py`, §0). The TigerGraph-native path
(`Featurizer.installAlgorithm("tg_pagerank"/"tg_louvain")` — `Featurizer` import verified) is
implemented behind the live graph modes and expected to fail INSTALL on this box; document the
attempt result honestly, same pattern as the MCP tier.

| Algorithm | Deterministic implementation | Named UI purpose (per 11.1) |
|---|---|---|
| **PageRank** | `nx.pagerank` over the advisor–household–referral graph (`advisor_serves_household` 360, `advisor_has_crm_referral`, `referral_for_household`, `referral_generates_crm_opportunity` edges — all present in `data/sample/edges/`) | **"Referral Network Position"** on CRM Activities + Advisor 360: advisor's PageRank percentile within the firm, rendered as a plain sentence ("strong referral hub — connected to N referral chains, top X % of the firm") with the raw score in evidence. Feeds Section 10 mentor selection later. |
| **Louvain** | `nx.community.louvain_communities(seed=42)` over an advisor–advisor kNN graph (k=5, cosine over the current embedding vectors — upgraded to GNN vectors in §7 automatically) | **"Peer Communities"** on the AGP page: discovered cohorts with real membership lists; each community card shows its distinguishing features (top-3 features by z-score vs firm mean) so the cohort is explainable, not just a number. |
| **Similarity** | existing panels (`app/embeddings/similar_entities.py`) — unchanged interface, upgraded vectors per §7/§8 | Similar Advisors/Households/Accounts, peer benchmarking. |

Persistence: one SQLite table `graph_metrics(entity_type, entity_id, metric, value, run_id,
computed_at)` in the existing feature-store DB + `POST /graph-insights/recompute` +
`GET /graph-insights/{advisor_id}` API. Recompute is on-demand/scripted (seconds for this graph
size), never on boot. No algorithm beyond these three — each has a screen; anything more repeats
the "Learning State" mistake.

---

## 7. GNN — three tiers, exactly per 11.1

**Node features (all tiers):** advisors = the 33 Feature_Catalog values (z-scored, None→0 +
missing-mask bits); households = `[total_aum, trailing 6m revenue, revenue slope, tx count,
segment/risk one-hot]`; accounts = `[current_value, account_type one-hot]`. **Features are the
GNN's INPUT; the learned 32-dim embeddings are its OUTPUT** — never conflate in UI or docs.

- **Tier 1 — `pyTigerGraph[gds]` `neighborLoader`** (needs live edges). Bounded attempt only:
  start the existing container, load ONLY `advisor_serves_household` (360 edges) +
  `household_owns_account` (720) + `advisor_has_crm_referral` (small) — NOT the 126-type/109K
  full load that stalled in Phase 2. **Time-box: 30 minutes wall-clock including container
  start.** If loaders or the built-in `GraphSAGEForVertexClassification` don't come up cleanly,
  record the exact failure in PROGRESS.md and the model card, and move on. (Note: the built-in
  model itself requires torch-geometric — verified by its own ImportError — so Tier 2's install
  is a prerequisite for Tier 1 anyway.)
- **Tier 2 — local PyG GraphSAGE — design this as the PRACTICAL DEFAULT.** `pip install
  torch-geometric` (2.8.0 wheel confirmed). Build a `HeteroData` from `FoundationGraphStore`
  (advisor/household/account node types; serves/owns edge types + an aggregated
  household–product "transacted" edge). Model: 2-layer `SAGEConv` hidden 64 → out 32, wrapped
  with `to_hetero`. **Training objective: self-supervised link prediction** on
  `advisor_serves_household` + `household_owns_account` with negative sampling (works without
  labels; embeddings are then generically useful for similarity). Hold out 10 % of edges;
  **print link-pred ROC-AUC** as the real metric. Time-box: ≤50 epochs, hard cap 10 min;
  reduction fallback hidden 32 / 1 layer, recorded honestly. This is the same model as Tier 1 —
  same architecture, real training — just fed from memory instead of TigerGraph's loader; the
  model card states which tier actually ran.
- **Tier 3 — deterministic feature-projection** (current `app/embeddings/service.py`) — final
  fallback, untouched.

**Output storage:** 32-dim vectors per advisor/household/account written through the
`VectorClient` (§8) with `model_name="graphsage-v1"`, `model_version` = registry version. In
`MODEL_CLIENT_MODE=real`, `EmbeddingSimilarityService`/`similar_entities` read the newest
registered embedding set (registry lookup by entity_type), so Similar-Advisors/Households panels
and §6's Louvain kNN graph upgrade automatically; deterministic mode keeps today's vectors —
nothing breaks either way.

---

## 8. Vector storage split — `TigerGraphVectorClient`

**Chroma is untouched and out of scope** (RAG/document vectors only). New adapter for
graph-entity vectors, same house pattern (§1):

```python
class VectorClient(Protocol):
    def upsert_embeddings(self, entity_type: str, model_name: str, model_version: str,
                          vectors: dict[str, list[float]]) -> dict: ...
    def search(self, entity_type: str, vector: list[float], top_k: int = 5,
               exclude_id: str | None = None) -> list[dict]: ...   # [{entity_id, score}]
    def describe(self) -> dict: ...
```

- `VECTOR_CLIENT_MODE=local|tigergraph`, default `local`.
- **`LocalVectorClient` (default, always works):** the existing SQLite `embeddings` table
  (`app/embeddings/service.py:70-77`) + brute-force cosine — at 360 households / 720 accounts an
  index would be decoration, and this is exactly the "deterministic fallback = current
  feature-projection similarity" 11.1 asks for.
- **`TigerGraphVectorClient`:** GSQL `ALTER VERTEX ... ADD VECTOR ATTRIBUTE emb(DIMENSION=32,
  METRIC="COSINE")` + upsert via the existing RESTPP payload builder + `vectorSearch()` GSQL for
  search (TigerVector, TG 4.2+).
- **Empirical support check FIRST — do not assume version support:** committed script
  `scripts/check_tg_vector_support.sh`: start the existing container, print `gsql --version`,
  attempt the `ALTER VERTEX` on a scratch vertex type + a 3-vector upsert + one `vectorSearch()`
  round-trip; print PASS/FAIL with raw output; write the result into the registry
  (`vector_backend_verified: true/false/date`) and PROGRESS.md. Time-box 20 minutes. FAIL is an
  acceptable, documented outcome — `local` stays the working default; the client-site cutover is
  env-only, same as every other adapter.

---

## 9. Isolation Forest — vulnerable-client / unusual-activity detection

**Model (mechanical):** `sklearn.ensemble.IsolationForest(n_estimators=200, contamination=0.05,
random_state=42)` at household level, fit on all household-cut rows, scored on the latest
period. Artifact + registry entry like every other model; surfaced through
`ModelClient.anomaly_scores`.

**Feature selection — deliberately "unusual vs the household's OWN history," not "unusual vs
other households"** (peer-relative anomaly on wealth data mostly flags "rich" or "poor," which
is both useless and unfair): max |z| of last-3-months monthly revenue vs own trailing-12m
mean/std; largest single transaction ÷ own 12m median tx size; tx-frequency ratio (3m rate ÷
prior-9m rate); revenue slope break (last-3m slope − prior-9m slope, own-history scaled); days
since last activity ÷ own median inter-transaction gap; share of last-3m revenue from a single
transaction. Segment/AUM are **excluded** as inputs precisely so wealth level cannot drive the
flag.

**Responsible presentation (the reason this item is Fable-designed) — binding rules:**
1. **Name the pattern, not the person.** Card title "Activity Pattern Review", flag copy
   "Unusual activity pattern — review suggested." The words "vulnerable", "at-risk client",
   "suspicious" never appear in UI copy.
2. **Care framing, capped volume.** Positioned as a service prompt ("consider scheduling a
   check-in"), amber/slate styling only — never the red/critical severity token; no
   "most anomalous" leaderboard; contamination=0.05 caps flags at ~5 % by construction; visible
   only within the advisor's own scope.
3. **Evidence always attached.** The flag expands to the household's own 12-month activity chart
   with the anomalous window marked, plus the top deviating signals in plain language ("3
   withdrawals in May, each >4× this household's typical transaction size") — "differs from this
   household's own pattern," never a peer comparison.
4. **Explicit uncertainty + human disposition.** Fixed copy: "Statistical flag, not a
   determination." Two actions: "Schedule review" and "Reviewed — expected activity"; the
   dismissal persists (feedback pipeline) and suppresses re-flagging that household for the same
   window.
5. **No speculative narration.** The LLM is never asked to guess causes (health, age, family) —
   any generated text is restricted to restating the statistical evidence.
6. **Model card states the false-positive expectation** ("at 5 % contamination on 360 households,
   ~18 flags; most will be benign") — the demo should say this out loud.

Placement (bounded): a flag column + detail drawer in the Advisor 360 households table, reusing
Phase-0 shared components; no new page.

---

## 10. Model registry + model cards — tabs inside the existing Admin page

- **Backend:** `app/ml/registry.py`. Committed `models/registry.json` (metrics + metadata only);
  binary artifacts in `models/artifacts/` (add to `.gitignore`; dir contains a `.gitkeep`).
  Entry fields (per 11.1): `name, version, algorithm` (including **which GNN tier actually
  ran** and which forecast model won), `training_date, training_data` (source files, sample
  frame, label definition text), `metrics` (the real printed numbers from §3.4/§5/§7),
  `features` (input list), `caveats` (small-data text verbatim), `artifact_path,
  artifact_sha256, quality_gate` (§2), `served_since`.
- **Training scripts, one per model, each re-runnable and cache-respecting** (skip if artifact
  hash current unless `--force`): `scripts/train/train_revenue_decline.py`, `train_agp_off_track.py`,
  `train_household_churn.py`, `train_revenue_forecast.py`, `train_graphsage_embeddings.py`,
  `train_anomaly_detector.py`, plus `scripts/train/run_all.py`. Each prints its full metrics
  block and updates the registry atomically. **Nothing trains on boot** — `RealModelClient` only
  loads.
- **Frontend:** add shadcn `Tabs` to `AdminHealthWorkspace` (`frontend/components/admin/
  admin-health-workspace.tsx` — currently 136 lines, no tabs): "System Health" (existing content,
  unchanged) | "Model Registry" (table: name, version, algorithm, trained, primary metric,
  served_by-live indicator) with a card drawer per model showing the full model card, including
  caveats prominently, using shared design-system primitives. New `GET /admin/models` +
  `GET /admin/models/{name}` routes. (11.11's Model Strategy / AI Protections tabs slot in beside
  this later — do not build them now.)

---

## 11. Env additions (`.env.example`)

```
MODEL_CLIENT_MODE=deterministic        # deterministic | real
VECTOR_CLIENT_MODE=local               # local | tigergraph
ML_ARTIFACTS_DIR=models/artifacts
ML_TIME_BOX_MINUTES=10                 # hard wall-clock cap per training script
```

---

## 12. Implementation sequence (commit-sized, with dependencies)

| # | Commit | Depends on | Verification gate (real output, committed to evidence/) |
|---|---|---|---|
| 1 | `pip install torch-geometric`; `app/ml/` skeleton: Protocol, errors, `DeterministicModelClient`, factory, settings fields, registry module, `.env.example`, gitignore for `models/artifacts/` | — | backend boots; `MODEL_CLIENT_MODE=deterministic` → `/predictions/A001` byte-identical to today |
| 2 | Dataset builders (`app/ml/training/datasets.py`): household frame + 3 label builders + anti-leakage assertions; prints prevalence report | 1 | printed report matches §0's measured numbers (n=2,159, 26.6 %, 3.8 %, 960/64 %) |
| 3 | Train scripts + artifacts + registry entries for the 3 XGBoost classifiers (§3) | 2 | metrics blocks printed; leakage tripwire clean; A001 anchor assertion passes |
| 4 | `RealModelClient.score_risk` + SHAP mapping (§4) + live-path wiring & precedence (§2) + `verify_contributions.py` before/after; then retire the dormant path | 3 | before/after table for A001 + one more advisor; endpoint schema unchanged; two advisors give different real-mode scores |
| 5 | Household churn surface (Advisor 360 / Client 360 household tables) | 3, 4 | screenshot, two advisors |
| 6 | GRU forecast: training + `/predictions/forecast/{id}` + Recharts band (§5) | 1 | sMAPE vs both baselines printed; screenshot |
| 7 | Classical algorithms (networkx PageRank + Louvain) + `graph_metrics` + Referral Position & Peer Communities UI (§6) | 1 | real scores for 60 advisors; screenshots |
| 8 | GNN Tier 2 (PyG hetero GraphSAGE) + embedding registry integration; then the bounded Tier-1 attempt (30 min box) (§7) | 1 (7 benefits) | link-pred AUC printed; tier recorded; Similar-panels diff before/after vectors |
| 9 | `VectorClient` (local impl live; `check_tg_vector_support.sh` run once, result recorded) (§8) | 8 | script PASS/FAIL output committed |
| 10 | Isolation Forest + Activity Pattern Review presentation (§9) | 2 | flag count ≈ 5 %; screenshot showing evidence drawer + dismissal |
| 11 | Admin "Model Registry" tab + `/admin/models` (§10) | 3–10 (renders whatever exists) | screenshot; registry lists every trained model with real metrics |

Items 6, 7, 10 are mutually independent after commit 2-3 — reorder freely if one blocks.

## 13. Top risks

1. **Anything requiring the live TigerGraph engine on this 2-core box** (GNN Tier 1 edge load,
   vector-support check, native GDS install). All three are designed fallback-first with hard
   time-boxes (30/20 min) and an honest documented-failure path; none can block the section.
2. **AGP label leakage** (status is computed from attainment): mitigated by the explicit feature
   exclusion list (§3.3) and the AUC>0.97 tripwire; expect a modest, honest AUC.
3. **Churn class rarity (3.8 %, 83 positives):** class weighting + PR-AUC-primary + a card that
   names the proxy nature of the label. If PR-AUC misses the 3×-base-rate gate, the model simply
   never serves (precedence rule) — the demo stays honest by construction.
