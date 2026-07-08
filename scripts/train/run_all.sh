#!/usr/bin/env bash
# Full ML/GNN training orchestrator (CLAUDE.md Section 11.1). Runs EVERY training script in
# dependency order with PYTHONPATH set and a per-step time-box, tolerant of individual failures
# (a missing optional dep — e.g. torch-geometric — skips only that step, not the whole chain).
#
# Prerequisites:
#   - Deps installed:  uv pip install -e ".[ml,gds]"   (or the codespace's pre-provisioned env)
#   - Graph data loaded (mock is fine): the trainers read the FoundationGraphStore / feature store.
#   - MODEL_CLIENT_MODE=real so trained artifacts are written under $ML_ARTIFACTS_DIR.
#
# Artifacts land in models/artifacts/*.joblib|*.pt ; registry in models/registry.json.
# Each step re-runs safely and asserts the anchored A001 figures are intact.
set -uo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH="${PYTHONPATH:-.}"
export MODEL_CLIENT_MODE="${MODEL_CLIENT_MODE:-real}"
export ML_TIME_BOX_MINUTES="${ML_TIME_BOX_MINUTES:-10}"

# Order: tabular classifiers -> forecast -> GNN embeddings -> anomaly -> outcome-driven fine-tune.
STEPS=(
  "train_revenue_decline.py"        # REVENUE_DECLINE_RISK  (XGBoost, household x cut)
  "train_household_churn.py"        # household churn        (XGBoost)
  "train_agp_off_track.py"          # AGP_OFF_TRACK_RISK     (XGBoost)
  "train_revenue_forecast.py"       # monthly revenue        (GRU/LSTM forecast)
  "train_graphsage_embeddings.py"   # GraphSAGE node embeddings (PyG; needs torch-geometric)
  "train_anomaly_detector.py"       # activity anomaly       (IsolationForest)
  "train_fl_finetune.py"            # outcome-driven GNN fine-tune (Section 11.3)
)

FAILED=()
for s in "${STEPS[@]}"; do
  echo; echo "############ TRAIN: $s ############"
  # PYTHONPATH=. (exported above) makes `import app...` resolve when run from repo root.
  if python "scripts/train/$s"; then
    echo "OK: $s"
  else
    echo "SKIPPED/FAILED: $s (see output above — likely a missing optional dep)"
    FAILED+=("$s")
  fi
done

echo; echo "======== TRAINING SUMMARY ========"
python - <<'PY'
import json, pathlib
p = pathlib.Path("models/registry.json")
if p.exists():
    d = json.loads(p.read_text())
    entries = d if isinstance(d, list) else d.get("entries", d)
    print(f"registry entries: {len(entries)}  ->  models/registry.json")
else:
    print("no models/registry.json yet")
PY
[ ${#FAILED[@]} -eq 0 ] && echo "All steps completed." || printf 'Skipped/failed: %s\n' "${FAILED[*]}"
