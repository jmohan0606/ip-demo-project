# Section 11.3 Design — FL = Feedback Loop: Outcome-Driven GNN Learning

_Fable-architect design document, 2026-07-06. Design only — the main thread (Opus) implements,
commit-by-commit, per §8. Every claim grounded against the real repo/data; citations are
`file:line` or real command output._

**Framing (the correction, stated first so it cannot be lost):** "FL" is the **Feedback Loop**,
NOT Federated Learning. Do not build FedAvg or any distributed-training simulation. The build
target: recorded recommendation outcomes (successful/unsuccessful) feed back into the GNN's
learned embeddings — a deeper layer ON TOP of the verified bandit weight loop — so the system's
"sense of what similar situations look like" shifts based on what has actually worked.
Client-facing copy: **"outcome-driven learning" / "the feedback loop"** — never "Federated
Learning" or "RLHF" as literal terms (both are analogies at best).

---

## 0. Verified current state (checked directly, not remembered)

| Fact | Evidence |
|---|---|
| Bandit loop (11.2) is real and stays untouched | `app/feedback/service.py:12-18` ACTION_SIGNALS (ACCEPT .6/+.05, COMPLETE 1.0/+.10, MODIFY .3/+.02, IGNORE −.1/−.02, REJECT −.5/−.08); `app/recommendations/service.py:77-86` `apply_delta` w←clamp(w+δ, 0.5, 1.5); replay in `impact_trend` (`service.py:174-290`); bandit spec `service.py:113-157`. |
| GNN graphsage-v1 (11.1 §7) | `app/ml/gnn.py`: homogeneous 2-layer SAGEConv, node-feature dim **8** (3 type one-hot + degree + 4 z-scored per-type slots, `gnn.py:110-124`), 1,140 nodes (60 ADVISOR/360 HOUSEHOLD/720 ACCOUNT), edges = `advisor_serves_household` (360) + `household_owns_account` (720), self-supervised link prediction, seed 42, 90/10 edge split, held-out ROC-AUC 0.9234, OUT_DIM 32. **Only embeddings + a JSON metadata marker are persisted (`gnn.py:196-220`) — no `state_dict` artifact exists today**; fine-tuning needs one (§4.2). |
| VectorClient | `app/ml/vector_client.py`: `gnn_embeddings` SQLite table PK `(entity_type, entity_id, model_name)` — multiple model versions coexist by construction. **Gap: `_rows` hardcodes `model_name='graphsage-v1'` (`vector_client.py:84`)**, so `search`/`get` can never see a `-ft` model. Must be parameterized (§4.4). |
| Similar-search read path | `GET /graph-insights/similar/{entity_type}/{entity_id}` (`app/api/routers/graph_insights.py:27-37`); Louvain Peer Communities also read GNN vectors (PROGRESS.md 11.1 commit 8/9). |
| Feedback seed data — THE PROBLEM, confirmed by direct CSV scan | `docs/tigergraph_foundation/data/sample/vertices/phx_dm_{feedback_event,outcome_event,learning_signal}.csv`: 36 rows each. **All 36 learning signals: family CRM_EXECUTION** (signal_json actions ACCEPT 24/REJECT 12). **Outcomes: all REVENUE_IMPACT, min 0.0, max 30,593.5, 24 zeros, 0 negatives.** Feedback actions in CSV: ACCEPT 8/REJECT 7/DEFER 7/NOT_RELEVANT 7/COMPLETE 7 — note **DEFER/NOT_RELEVANT are not in the live ACTION_SIGNALS vocabulary** (which has MODIFY/IGNORE); all created_at 2026-06-28 (single date). All feedback targets REC_A0xx only. |
| Recommendation families (real, 3) | `app/recommendations/service.py:18-55` ACTION_FAMILIES: MANAGED_MIX (PRODUCT_MIX), RETENTION (REVENUE_AT_RISK), CRM_EXECUTION (AGP_EXECUTION + PIPELINE_ACCELERATION). Seed recs map 1:1: 60 × "Prioritize high-value CRM follow-up" = `REC_A001..A060` → advisor via `recommendation_for_advisor` (60 edges); 30 × "Review account concentration and product fit" = `REC_AC_AC00001..30` → account via `recommendation_for_account` (MANAGED_MIX); 30 × "Review relationship growth opportunity" = `REC_HH_H0001..30` → household via `recommendation_for_household` (RETENTION). |
| Chain edges all exist in schema + data | `phx_dm_feedback_for_recommendation`, `phx_dm_outcome_for_feedback`, `phx_dm_learning_from_outcome`, `phx_dm_learning_updates_recommendation` (`tigergraph/schema/02_edges.gsql:102-105`; 36 rows each in `data/sample/edges/`). |
| **Negative outcome_value is legal — no schema change needed** | `phx_dm_outcome_event.outcome_value` is `DOUBLE` (`tigergraph/schema/01_vertices.gsql:44`). All vertices/edges Part A needs already exist. |
| Manifest entries to bump | `data/manifest.json` orders 40/41/42 (3 vertex files, expected_rows 36) + the 4 chain-edge entries (expected_rows 36). Generator pattern to copy: `docs/tigergraph_foundation/scripts/expand_sample_data_v1_2.py` (deterministic `rng_for` via crc32, `read`/`append`/`update_manifest` helpers, idempotency via sentinel-row checks). Validator: `scripts/validate_package.py`. |
| CSV rows flow into the app | `FoundationGraphStore` loads manifest-listed CSVs from `data/sample/` (`app/graph/foundation_store.py:25,43-51`); runtime feedback submits are in-memory upserts through the same store (`app/graph/artifacts.py:6-33`, `app/feedback/service.py:48-92`) — the FL pair builder must read the store (seed + runtime rows), not the CSVs directly. |
| Live bandit weights (context for target numbers) | CRM_EXECUTION 1.50, MANAGED_MIX 0.53 (PROGRESS.md 11.2 verification) — the seeded story already has CRM succeeding and MANAGED_MIX being rejected. |
| Libraries | `torch 2.12.1+cpu`, `torch_geometric 2.8.0` — verified import. **No new installs needed.** |
| UI extension point | `frontend/components/recommendations/learning-state-showcase.tsx` (401 lines): beats (a) action signals, (b) weight trajectory replay, (c) baseline→learned per family, + 11.2 bandit panel. The FL panel becomes the new final beat. |
| Anchored guardrail figures | A001 revenue_ltm 387,293.22 / aum 10,018,200 / nnm_3m 102,080 / kpi 0.275; A020 539,262.90 / 25,990,000; F001 38,365,750.01. The feedback chain feeds none of these (no revenue/AUM/feature-snapshot linkage), so Part A cannot move them **by construction** — still assert after running, same as every 11.1 training script. |

---

## 1. Architecture in one picture

```
                         (existing, verified — UNTOUCHED)
feedback action ──► ACTION_SIGNALS reward ──► LearningWeightStore w←clamp(w+δ)   [simple visible layer]
      │
      └──► feedback → outcome → learning_signal graph chain (already persisted)
                                        │
                    (NEW, 11.3 — the deeper layer, additive)
                                        ▼
                 outcome-labeled pair builder  ──► contrastive fine-tune of graphsage-v1
                 (advisor/household/family,          (link-pred loss retained + margin loss)
                  positive vs negative)                          │
                                        ┌───────────────────────┘
                                        ▼
                 gnn_embeddings model_name="graphsage-v1-ft"  (v1 rows NEVER overwritten)
                                        │
              ┌─────────────────────────┼──────────────────────────────┐
              ▼                         ▼                              ▼
   /graph-insights/similar     per-(advisor,family)            Learning State Showcase
   (active-model resolution,   outcome affinity in rec         "Run Feedback-Driven
    ?model= override for       evidence (+ optional bounded    Retraining" before/after
    before/after)              confidence modifier)            panel
```

Both layers stay: the bandit multiplier is the direct suppressor of unsuccessful families; the
GNN layer changes what "similar situations" means, so peer evidence and situation-affinity stop
pointing at combinations that failed. Never delete graphsage-v1 or the bandit loop.

---

## 2. Part A — Outcome-variety data expansion (bounded, deterministic)

### 2.1 Concrete finish line (exact numbers — this is the whole target, stop here)

Add **144 new (feedback, outcome, learning_signal) triples** — 1:1:1, matching the existing seed
structure — bringing each of the three vertex files **36 → 180 rows** and each of the four chain
edge files **36 → 180 rows**. Distribution (deterministic, seeded):

| Family | New triples | Positive label | Negative label | Rationale |
|---|---|---|---|---|
| CRM_EXECUTION | 36 | 26 | 10 | already the "works" family (weight 1.50) — mostly succeeds, now with real failures too |
| MANAGED_MIX | 54 | 20 | 34 | the "keeps failing" family (weight 0.53) — the FL story's suppression case |
| RETENTION | 54 | 34 | 20 | previously ZERO labeled feedback — now well covered, net-positive |
| **Total new** | **144** | **80** | **64** | grand total 180 signals · 3 families · both polarities in every family |

Label rule (exactly the 11.3 spec): **positive** = action in {ACCEPT, COMPLETE} with
`outcome_value ≥ 0`; **negative** = REJECT/IGNORE, **or COMPLETE with `outcome_value < 0`**
(the genuinely-new "completed but it hurt" case — 20 of the 64 negatives are
completed-with-negative-impact, spread across all 3 families).

### 2.2 Row construction (exact)

- **IDs**: `FB_FL0001..FB_FL0144`, `OUT_FL0001..`, `LS_FL0001..` — disjoint from seed `*_A0xx`
  and runtime `FB_{hex8}` ids. The `_FL` prefix is also the generator's idempotency sentinel.
- **Actions**: use the **live ACTION_SIGNALS vocabulary only** (ACCEPT/COMPLETE/MODIFY/IGNORE/
  REJECT) — not the seed's DEFER/NOT_RELEVANT. Positive rows: mix of ACCEPT/COMPLETE (~40/60);
  negative rows: REJECT (~55%), IGNORE (~15%), COMPLETE-with-negative-outcome (~30%). A few
  MODIFY rows (counted positive, small reward) for realism — cap at 8 total.
- **Outcomes** (one per feedback, mirroring seed structure): positives → `REVENUE_IMPACT`,
  value deterministic in **$1,500–$45,000**; completed-negatives → `REVENUE_IMPACT`, value in
  **−$25,000 … −$2,000** (the first negative outcome_value rows in the dataset — schema `DOUBLE`,
  verified legal); REJECT/IGNORE → `ACTION_TAKEN`, value 0 (matches live-service semantics,
  `app/feedback/service.py:60-69`). Round to cents.
- **Dates**: `created_at` spread weekly over **2026-01-05 … 2026-06-28** (26 weekly buckets,
  ~5-6 events/week) — gives the replay/trajectory a real time dimension instead of one date.
  `observed_at` = created_at + 3–21 days (deterministic per row), never past 2026-07-03.
- **Recommendation targets** (existing recs only — no new recommendation rows):
  CRM_EXECUTION → `REC_A037..A060` + repeats of `REC_A001..A036` (some recs legitimately get a
  second feedback event later in time); MANAGED_MIX → `REC_AC_AC00001..30` (54 events over 30
  recs → repeats are realistic follow-up feedback); RETENTION → `REC_HH_H0001..30` (54 over 30).
- **learning_signal fields**: `signal_type=RECOMMENDATION_FEEDBACK`; `reward`/`score_delta` from
  the live ACTION_SIGNALS table (COMPLETE-with-negative-impact rows get reward adjusted −0.20
  per the outcome-adjustment table in `service.py:135-139`, clamped [−1,1] — document this in
  signal_json); `signal_json` = `{"action","family","outcome_value","label":"positive|negative",
  "source":"SEEDED_OUTCOME_HISTORY"}`.
- **Edges**: +144 rows each to `phx_dm_feedback_for_recommendation` (FB→REC),
  `phx_dm_outcome_for_feedback` (OUT→FB), `phx_dm_learning_from_outcome` (LS→OUT),
  `phx_dm_learning_updates_recommendation` (LS→REC). Every referenced REC id exists (verified
  against the 120-row recommendation file).

### 2.3 What changes on disk (complete list — nothing else)

| File | Rows now | Rows after |
|---|---|---|
| `vertices/phx_dm_feedback_event.csv` | 36 | 180 |
| `vertices/phx_dm_outcome_event.csv` | 36 | 180 |
| `vertices/phx_dm_learning_signal.csv` | 36 | 180 |
| `edges/phx_dm_feedback_for_recommendation.csv` | 36 | 180 |
| `edges/phx_dm_outcome_for_feedback.csv` | 36 | 180 |
| `edges/phx_dm_learning_from_outcome.csv` | 36 | 180 |
| `edges/phx_dm_learning_updates_recommendation.csv` | 36 | 180 |
| `data/manifest.json` | expected_rows 36 ×7 entries | expected_rows 180 ×7 entries |

**No schema changes. No new vertex/edge types. No new manifest entries. Zero existing rows
touched (append-only).** Loading jobs are per-file and column-order stable — unchanged.

### 2.4 Generator + guardrails

New sibling script `docs/tigergraph_foundation/scripts/expand_outcome_variety_v1_3.py`
(don't graft onto v1_2 — its steps are already idempotency-gated as a unit; a sibling keeps the
bounded scope reviewable). Reuse v1_2's exact helpers/pattern: `rng_for(*key)` crc32-seeded
determinism, `read`/`append`, manifest expected_rows bump, `--verify`-style distribution print.
Idempotent: skip everything if `FB_FL0001` already present.

Guardrails (same as 9.3/11.9, enforced not asserted):
1. Append-only — the script never rewrites an existing row (use `append`, never `write`, for the
   7 data files).
2. After running: `scripts/validate_package.py` → 0 discrepancies; then recompute A001/A020/F001
   anchors through the normal snapshot path and assert exact equality (same tripwire as every
   11.1 training script) — the chain can't move them, but prove it anyway.
3. The script prints the full family × polarity × action distribution table (the §2.1 numbers)
   as its verification output, committed to `docs/section11/evidence/`.

---

## 3. Part B — Pair construction from the real chain (exact)

The pair builder (`app/ml/fl_pairs.py`) reads the **graph store** (so it sees seeded rows AND any
runtime-submitted feedback — real recorded history, not a parallel table):

**Chain walk per learning signal** `LS`:
`LS ──learning_updates_recommendation──► REC`, `LS ──learning_from_outcome──► OUT
──outcome_for_feedback──► FB` (action, created_at). Family from `signal_json.family`; fallback:
map REC title → family via ACTION_FAMILIES. Label per §2.2's rule. Legacy-vocabulary mapping —
read-time only, seed rows untouched: `DEFER→IGNORE`, `NOT_RELEVANT→REJECT`.

**Entity resolution per event** (all edges verified present):
- `REC_A0xx` → advisor via `recommendation_for_advisor`; household = none (advisor-level event).
- `REC_HH_Hxxxx` → household via `recommendation_for_household`; advisor = serving advisor via
  inbound `advisor_serves_household`.
- `REC_AC_ACxxxxx` → account via `recommendation_for_account` → household via inbound
  `household_owns_account` → serving advisor.

Yields labeled events `e = (family f, advisor a, household h|None, polarity ±, created_at)`.

**Pairs (node-index pairs into the existing homogeneous GNN graph — no new node types, so the
graph build in `gnn.py:_build_graph` is reused unchanged):**

| Pair type | Construction | Direction |
|---|---|---|
| P1 same-situation pull | advisor pairs (a_i, a_j), both **positive** in the **same family** f | pull together |
| P2 failure-contrast push | advisor pairs (a⁺, a⁻): a⁺ positive in f, a⁻ **negative in the same f** | push apart |
| P3 relationship pull | (advisor, household) from one **positive** event | pull together |
| P4 relationship push | (advisor, household) from one **negative** event | push apart |

Framed simply (this sentence is the client-facing explanation): *"Advisors for whom a given kind
of action keeps working end up close together; an advisor for whom it keeps failing drifts away
from that group — so 'peers like you succeeded with this' stays honest."*

Determinism + bounds: sort events by (created_at, LS id); per family cap P1/P2 via seeded
sampling at **600 pairs each**, P3/P4 uncapped (≤144). Total ≤ ~3,800 pairs — trivial on 2 cores.
**Hold out 20% of pairs (seeded split, stratified by type+family) as the evaluation set** — the
separation metric (§4.3) is computed on held-out pairs only, never on pairs trained on.

Expected volume on the expanded data (before capping): CRM 26⁺/10⁻ → P1 C(≥26,2)≈325, P2
26×10=260; MANAGED_MIX P1 C(20,2)=190, P2 20×34=680→600; RETENTION P1 C(34,2)=561, P2 680→600.
Real signal, not two pairs and a prayer — but still demo-scale (state it in the model card).

---

## 4. Part B — Contrastive fine-tune of graphsage-v1

### 4.1 Loss (additive to the existing objective, which is retained)

Fine-tune minimizes **L = L_linkpred + λ·L_contrastive**, λ = 0.5:

- `L_linkpred` — the exact existing BCE-with-negative-sampling term (`gnn.py:171-183`), same
  train edges/split (seed 42 reproduces the identical 90/10 split). Keeping it is the anti-
  catastrophic-forgetting anchor: embeddings must keep encoding the graph, not just the outcomes.
- `L_contrastive` — cosine-margin pairwise loss on TRAIN pairs, ẑ = L2-normalized embeddings:
  - pull (P1, P3): `1 − cos(ẑ_u, ẑ_v)`
  - push (P2, P4): `max(0, cos(ẑ_u, ẑ_v) − m)`, margin **m = 0.2**
  - mean over pairs, pair types equally weighted (P3/P4 batch-weighted ×0.5 so relationship
    pairs don't dominate P1/P2's family semantics).

(A margin loss over an InfoNCE formulation deliberately: with 3 families and ~60 advisors,
InfoNCE's in-batch-negatives assumption is noisy at this scale; margin pairs are directly
readable and each term maps to one recorded outcome pair — better for the evidence bar.)

### 4.2 Procedure (bounded, deterministic, 2-core safe)

1. **Prerequisite (small additive change to `gnn.py`)**: `train_gnn()` also saves
   `models/artifacts/graphsage-v1.pt` (`state_dict` + the node index list) — today only
   embeddings + a JSON marker persist (`gnn.py:196-220`). If the artifact is absent at fine-tune
   time, run `train_gnn()` first (reproducible, seed 42, AUC ≈0.9234).
2. Load state_dict; freeze nothing (the model is ~15K params); optimizer Adam **lr = 1e-3**
   (10× lower than base training) — a fine-tune, not a retrain.
3. **≤ 20 epochs**, early-stop when held-out link-pred AUC drops > 0.02 below its starting value
   or held-out separation (§4.3) stops improving for 5 epochs; hard wall-clock cap =
   `ml_time_box_minutes` (same setting the base trainer already respects, `gnn.py:164`).
   Seeds: torch/np = 42 → the run is idempotent for a fixed feedback history.
4. Persist ALL 1,140 embeddings through the VectorClient with
   **`model_name="graphsage-v1-ft"`, version "1.0.{n}"** where n = count of labeled events used
   (a version that honestly encodes what history the model has seen). The table PK
   `(entity_type, entity_id, model_name)` means **graphsage-v1 rows are untouched by
   construction** — before/after stays comparable forever.
5. Registry entry `graphsage-v1-ft` (via `app/ml/registry.upsert_entry`): algorithm "GraphSAGE +
   outcome-contrastive fine-tune (feedback loop)", `label_definition` = the §2.2 polarity rule +
   §3 pair table verbatim, metrics (§4.3), caveats: "Demo-scale: fine-tuned on N recorded
   outcome events (seeded history + any live feedback); effect sizes are directional evidence
   the loop works, not production learning curves."

### 4.3 Metrics + quality gate (real numbers, printed, never asserted)

| Metric | Definition | Gate |
|---|---|---|
| `link_pred_auc_before/after` | same held-out 10% edge split as v1 | **retention gate: after ≥ before − 0.03**, else `quality_gate: failed` → `-ft` never becomes active; v1 keeps serving |
| `separation_before/after` | on **held-out** pairs: mean cos(pull pairs) − mean cos(push pairs), under v1 vs -ft embeddings | report honestly; **no minimum** — if the shift is small, the UI says so (§6) |
| `per_family_separation` | same, split by family | the MANAGED_MIX number is the demo's money stat |
| `pairs_used` | counts by type × family × train/holdout | printed table |

### 4.4 Active-model resolution (fixes the real VectorClient gap)

- `LocalVectorClient._rows/get/search` gain a `model_name: str | None = None` parameter
  (replacing the hardcode at `vector_client.py:84`); `None` resolves via a new helper
  `app/ml/registry.active_embedding_model()` → `"graphsage-v1-ft"` iff its registry entry
  exists AND `quality_gate == "passed"`, else `"graphsage-v1"`. Protocol updated; the
  TigerGraph client delegates unchanged.
- `GET /graph-insights/similar/...` gains optional `?model=graphsage-v1|graphsage-v1-ft`
  (default = active) — this is the before/after mechanism. Louvain Peer Communities read the
  active model transparently (communities may legitimately shift after retraining — note it in
  PROGRESS.md when it happens, it's the feature working, not a regression).

### 4.5 Outcome-affinity read path (how the deeper layer visibly touches recommendations)

At fine-tune time, compute per family f the centroids `c_f⁺`/`c_f⁻` of advisors with
positive/negative recorded outcomes in f (under the new embeddings) and persist a small
`fl_family_affinity(advisor_id, family, affinity, model_name, computed_at)` SQLite table
(same DB). `affinity(a, f) = cos(ẑ_a, c_f⁺) − cos(ẑ_a, c_f⁻)` ∈ [−2, 2], practically ~[−0.5, 0.5].

Consumption — additive and bounded, so the verified ranking is never destabilized:
- **Always**: `RecommendationService.generate_for_advisor` attaches
  `outcome_affinity: {value, sentence}` to each rec's evidence/reasoning trace — e.g. *"Advisors
  in situations like this one have a positive recorded track record with Managed Mix actions
  (affinity +0.21, outcome-driven learning)"*. Evidence first — this alone satisfies "visibly
  wired".
- **Behind `FL_AFFINITY_IN_CONFIDENCE=true` (default true)**: confidence ×
  `clamp(1 + 0.15·tanh(2·affinity), 0.90, 1.10)` — a ±10% bounded confidence modifier, shown in
  the reasoning trace as its own step. It does NOT multiply priority_score: the bandit weight
  (`service.py:135-137`) remains the sole ranking lever; the two layers stay separately
  attributable (bandit = family-level suppression; GNN = situation-level evidence/confidence).

---

## 5. Backend endpoints (extend `app/api/routers/feedback_learning.py` — no new router)

| Endpoint | Behavior |
|---|---|
| `POST /feedback-learning/retrain` | Body `{dry_run: bool = false}`. Builds pairs from the store's full recorded history (§3), runs the fine-tune (§4.2; `dry_run` stops after the pair/metric preview), writes `-ft` embeddings + affinity table + registry entry. Returns the full §4.3 metrics block + wall time + `events_used`. Idempotent for unchanged history (seeded); re-running after NEW live feedback legitimately produces a new `1.0.{n}`. |
| `GET /feedback-learning/before-after?advisor_id=A012&top_k=5` | The demo payload: `{available, advisor_id, similar_before: [..model=graphsage-v1], similar_after: [..model=graphsage-v1-ft], rank_moves: [{entity_id, before_rank, after_rank}], affinity: [{family, before, after, delta}], separation: {overall_before, overall_after, per_family}, model_versions}`. `available:false` + hint when `-ft` doesn't exist yet. Affinity "before" = affinities computed once under v1 embeddings at retrain time (stored alongside, `model_name` column) — never fabricated. |
| `GET /feedback-learning/state` | additive key `outcome_learning: {active_model, last_retrain, events_used, gate}` |

Reuse: `impact_trend`/bandit endpoints untouched.

---

## 6. UI — "Run Feedback-Driven Retraining" on the Learning State Showcase

Extend `frontend/components/recommendations/learning-state-showcase.tsx` with a final section
**"Outcome-Driven Learning — the Deeper Layer"** (keep beats a/b/c + bandit panel exactly as-is
above it; this is the loop's second story, told after the simple one):

1. **Explainer strip** (static copy): two-layer diagram sentence — *"Layer 1 (above): feedback
   moves a family's ranking weight instantly. Layer 2 (below): recorded outcomes periodically
   reshape the graph's own sense of which situations are alike — outcome-driven learning."*
2. **BEFORE column** (rendered from `GET /before-after` pre-retrain, or from stored v1 numbers):
   selected advisor's top-5 similar advisors (v1 embeddings) + per-family affinity bars.
   Default advisor: one with heavy new MANAGED_MIX-negative history (pick the exact id from the
   generated data at implementation time; expose an advisor selector wired to the shell scope
   context like every other 9.1 page).
3. **Run button** → `POST /retrain`, spinner with live wall-time, then the real metrics block:
   pairs table, link-pred AUC before/after, separation before/after (overall + per family).
4. **AFTER column**: same two panels under `-ft`, with rank-movement badges (↑2/↓1/new) on the
   similar list and delta arrows on affinity bars (Phase-0 shared delta component, green/red).
5. **Honesty rendering (binding):** all numbers come from the response — nothing computed or
   invented client-side. If `|separation_after − separation_before| < 0.02`, render the amber
   note: *"On demo-scale outcome history this shift is small (X → Y) — the mechanism is real;
   the magnitude grows with recorded history."* If the retention gate failed: state that v1
   still serves and why. Never animate a delta that isn't in the payload.
6. All copy says **"outcome-driven learning" / "feedback loop"**; the card carries the standard
   "iPerform Insights and Coaching" proactive-surface label (11.11).

---

## 7. Honesty rules (restated as implementation requirements)

- graphsage-v1 embeddings, the bandit loop, and `DeterministicModelClient` fallbacks are never
  deleted or overwritten; `-ft` serves only past the retention gate; `?model=` keeps v1
  permanently inspectable.
- Every metric shown is printed by the training run and persisted in the registry entry /
  endpoint response; the UI is a renderer, not a calculator.
- Model card + UI state the small-data caveat verbatim; a small/negative result is displayed,
  not massaged (no re-tuning λ/m to make the demo number bigger — pick λ=0.5, m=0.2 once and
  report what happens).
- PROGRESS.md records: exact new row counts, distribution table, before/after metrics, whether
  Louvain communities shifted.

---

## 8. Implementation sequence (commit-sized, each with a real verification gate)

| # | Commit | Depends | Verification gate (output committed to `docs/section11/evidence/`) |
|---|---|---|---|
| 1 | Part A generator `expand_outcome_variety_v1_3.py` + run it + manifest bumps | — | distribution table matches §2.1 exactly (180/180/180 ×3 vertices, 180 ×4 edges); `validate_package.py` 0 discrepancies; A001/A020/F001 anchors assert; rerun script → "already applied, skipped" |
| 2 | `gnn.py` saves `graphsage-v1.pt` state_dict; VectorClient `model_name` parameterization + `active_embedding_model()`; `?model=` on `/graph-insights/similar` | — | base retrain reproduces AUC ≈0.9234; `/graph-insights/similar/ADVISOR/A020` byte-identical to the 11.1-verified result (A019 0.98 / A013 0.93 …) |
| 3 | `app/ml/fl_pairs.py` (chain walk + pair builder + legacy-vocab map + holdout split) | 1 | printed pairs table: counts by type × family × polarity consistent with §3's expected volumes; deterministic across two runs |
| 4 | `app/ml/fl_finetune.py` (loss, procedure, `-ft` persistence, affinity table, registry entry) | 2,3 | full §4.3 metrics block printed; retention gate evaluated for real; SQL check: `graphsage-v1` row count in `gnn_embeddings` unchanged (1,140) and `-ft` rows = 1,140 |
| 5 | Endpoints: `/retrain`, `/before-after`, `state` additive key; affinity evidence + bounded confidence modifier in `RecommendationService` | 4 | curl outputs for retrain + before-after committed; two different advisors → different affinity payloads; reasoning trace shows the affinity step; backend imports clean, route count |
| 6 | Showcase UI panel (§6) | 5 | Playwright: before→run→after screenshots (`docs/qa_screenshots/`), rank-move badges rendered from payload only, 0 console errors, `tsc` pass |
| 7 | `.env.example` (`FL_AFFINITY_IN_CONFIDENCE=true`) + PROGRESS.md + model-card visible in Admin Model Registry tab (renders automatically from the registry — verify, don't rebuild) | 4-6 | Admin tab screenshot shows `graphsage-v1-ft` with honest badge |

Commits 1 and 2 are independent — parallelizable. Everything else is strictly ordered.

## 9. Top risks

1. **Small effect size on demo-scale history** (144 seeded + ~dozens live events; 60 advisors).
   Mitigation: the per-family polarity skew (§2.1) makes MANAGED_MIX separation genuinely
   learnable; the holdout separation metric + §6.5's honesty rendering make a small result a
   presentable truth instead of a fake big one. The gate ensures a null result costs nothing
   (v1 keeps serving).
2. **Fine-tune degrading the graph structure the embeddings encode** (link-pred AUC drop, Louvain
   communities churning, Similar-panels regressing). Mitigation: retained link-pred loss, low lr,
   ≤20 epochs, −0.03 retention gate, v1 rows immutable, `?model=` keeps v1 inspectable; expected
   community shift documented as intended behavior.
3. **Ambiguity about "recorded history" sources** (seed CSVs use a different action vocabulary;
   runtime rows are in-memory per process). Mitigation: pair builder reads only the graph store
   with an explicit read-time vocab map (§3); `events_used` + version suffix `1.0.{n}` make
   exactly-what-was-learned-from auditable per run.
