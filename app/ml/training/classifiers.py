from __future__ import annotations

"""XGBoost risk classifiers (Section 11.1 §3) — the three real-label models.

This module lives under app/ml/training/, so heavy ML imports (xgboost, sklearn, joblib,
shap) are permitted here. Business code never imports this module — it consumes trained
artifacts through app.ml.client only.

Each trainer:
  - builds a real-label frame (app.ml.training.datasets),
  - applies the correct split (temporal for revenue models, group-by-advisor for AGP),
  - fits an XGBClassifier with the §2 baseline config,
  - prints a REAL metrics block (ROC-AUC, PR-AUC, Brier, precision@decile, calibration),
  - applies the quality-gate floor + the AUC>0.97 leakage tripwire,
  - saves a joblib artifact + writes a registry entry (metrics/metadata),
  - asserts the anchored A001 figures are still intact (shared-state tripwire).
"""

import datetime as _dt
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from app.ml import registry
from app.ml.training import datasets as ds

# §2 baseline config for all three classifiers
_XGB_BASE = dict(
    n_estimators=300, max_depth=4, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, random_state=42,
    tree_method="hist", n_jobs=2, eval_metric="logloss",
)

SMALL_DATA_CAVEAT = (
    "Demo-scale synthetic-seeded data; n≈2.2K household-period samples from 360 households "
    "/ 60 advisors. Metrics indicate the pipeline is real, not production accuracy."
)

_LEAKAGE_AUC = 0.97
# artifact "trained_at" is passed in (Date.now() unavailable in some contexts); scripts stamp it.


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d")


def _precision_at_top_decile(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    n = max(1, int(len(y_prob) * 0.1))
    order = np.argsort(-y_prob)[:n]
    return float(y_true[order].mean())


def _calibration_table(y_true: np.ndarray, y_prob: np.ndarray, bins: int = 5) -> list[dict]:
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < bins - 1 else y_prob <= hi)
        if mask.sum() == 0:
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": 0, "pred_mean": None, "obs_rate": None})
        else:
            out.append({
                "bin": f"{lo:.1f}-{hi:.1f}", "n": int(mask.sum()),
                "pred_mean": round(float(y_prob[mask].mean()), 3),
                "obs_rate": round(float(y_true[mask].mean()), 3),
            })
    return out


def _metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    return {
        "n": int(len(y_true)),
        "base_rate": round(float(y_true.mean()), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
        "brier": round(float(brier_score_loss(y_true, y_prob)), 4),
        "precision_at_top_decile": round(_precision_at_top_decile(y_true, y_prob), 4),
    }


def _fit(X_train, y_train, scale_pos_weight: float | None = None):
    import xgboost as xgb

    params = dict(_XGB_BASE)
    if scale_pos_weight is not None:
        params["scale_pos_weight"] = scale_pos_weight
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train)
    return model


def _print_block(title: str, train_m: dict, test_m: dict, calib: list[dict],
                 primary: str, floor: float, gate_passed: bool, leak: bool) -> None:
    print(f"\n{'='*72}\n{title}\n{'='*72}")
    print(f"  train: {train_m}")
    print(f"  test : {test_m}")
    print(f"  primary metric = {primary} = {test_m.get(primary)}  (floor {floor}) -> "
          f"{'PASS' if gate_passed else 'FAIL'}")
    if leak:
        print("  *** LEAKAGE SUSPECTED (held-out AUC > 0.97) — quality_gate FORCED to failed ***")
    print("  calibration (test):")
    for row in calib:
        print(f"    {row['bin']}: n={row['n']:>4}  pred={row['pred_mean']}  obs={row['obs_rate']}")


def _save_and_register(name: str, model, feature_cols: list[str], algorithm: str,
                       label_def: str, training_data: str, split_desc: str,
                       train_m: dict, test_m: dict, calib: list[dict],
                       primary: str, floor: float, gate_passed: bool) -> dict:
    art_dir = registry.artifact_dir()
    art_path = art_dir / f"{name}.joblib"
    payload = {
        "model": model, "feature_cols": feature_cols, "algorithm": algorithm,
        "primary_metric": primary, "trained_at": _now(),
    }
    joblib.dump(payload, art_path)
    import hashlib
    sha = hashlib.sha256(art_path.read_bytes()).hexdigest()[:16]
    entry = {
        "name": name, "version": "1.0", "algorithm": algorithm,
        "training_date": _now(), "training_data": training_data,
        "label_definition": label_def, "split": split_desc,
        "metrics": {"train": train_m, "test": test_m, "calibration": calib},
        "primary_metric": primary, "primary_metric_value": test_m.get(primary),
        "quality_floor": floor, "features": feature_cols,
        "caveats": SMALL_DATA_CAVEAT,
        "artifact_path": str(art_path), "artifact_sha256": sha,
        "quality_gate": "passed" if gate_passed else "failed",
        "served_since": _now() if gate_passed else None,
    }
    registry.upsert_entry(entry)
    return entry


def _assert_anchors_intact() -> None:
    """Shared-state tripwire (§3.6): recompute A001's snapshot through the normal path and
    assert the anchored figures are unchanged. Training reads CSVs only and never upserts,
    so this must always hold — it fails loudly if anything mutated shared state."""
    from app.features.engineering import FeatureEngineeringService

    vals = FeatureEngineeringService().compute_advisor_snapshot("A001").values()
    checks = {"revenue_ltm": 387293.22, "aum_total": 10018200, "nnm_3m": 102080}
    for k, expected in checks.items():
        got = float(vals.get(k, 0))
        assert abs(got - expected) < 0.5, f"ANCHOR DRIFT: A001.{k} = {got}, expected {expected}"
    print(f"\n  anchor check OK — A001 revenue_ltm={vals['revenue_ltm']} aum_total={vals['aum_total']} "
          f"nnm_3m={vals['nnm_3m']}")


# --------------------------------------------------------------------------------------
# Trainers
# --------------------------------------------------------------------------------------

_TRAIN_CUTS = {"2024-08", "2024-11", "2025-02", "2025-05"}
_TEST_CUTS = {"2025-08", "2025-11"}


def _household_split(frame: ds.HouseholdFrame, label_col: str):
    df = frame.df
    tr = df[df["cut"].isin(_TRAIN_CUTS)]
    te = df[df["cut"].isin(_TEST_CUTS)]
    cols = frame.feature_cols
    return (tr[cols].to_numpy(float), tr[label_col].to_numpy(int),
            te[cols].to_numpy(float), te[label_col].to_numpy(int), cols)


def train_revenue_decline() -> dict:
    frame = ds.build_household_frame()
    Xtr, ytr, Xte, yte, cols = _household_split(frame, "label_decline")
    model = _fit(Xtr, ytr)
    train_m = _metrics(ytr, model.predict_proba(Xtr)[:, 1])
    ptest = model.predict_proba(Xte)[:, 1]
    test_m = _metrics(yte, ptest)
    calib = _calibration_table(yte, ptest)
    floor, primary = 0.65, "roc_auc"
    leak = test_m["roc_auc"] > _LEAKAGE_AUC
    gate = (test_m[primary] >= floor) and not leak
    _print_block("REVENUE_DECLINE_RISK (household × cut, temporal split)",
                 train_m, test_m, calib, primary, floor, gate, leak)
    entry = _save_and_register(
        "revenue-decline-xgb", model, cols, "XGBoost (XGBClassifier, hist)",
        "rev(t, t+6m] < 0.85 × rev(t-6m, t] at household×cut level",
        "foundation sample: 15,116 revenue transactions / 360 households, cuts 2024-08…2025-11",
        "temporal — train cuts 2024-08…2025-05, test cuts 2025-08 & 2025-11",
        train_m, test_m, calib, primary, floor, gate)
    _assert_anchors_intact()
    return entry


def train_household_churn() -> dict:
    frame = ds.build_household_frame()
    Xtr, ytr, Xte, yte, cols = _household_split(frame, "label_churn")
    base = ytr.mean()
    spw = (1 - base) / base if base > 0 else 25.0
    model = _fit(Xtr, ytr, scale_pos_weight=spw)
    train_m = _metrics(ytr, model.predict_proba(Xtr)[:, 1])
    ptest = model.predict_proba(Xte)[:, 1]
    test_m = _metrics(yte, ptest)
    calib = _calibration_table(yte, ptest)
    primary = "pr_auc"
    floor = round(3 * float(yte.mean()), 4)  # PR-AUC gate = 3× base rate
    leak = test_m["roc_auc"] > _LEAKAGE_AUC
    gate = (test_m[primary] >= floor) and not leak
    _print_block("HOUSEHOLD_CHURN_PROPENSITY (severe attrition proxy, scale_pos_weight)",
                 train_m, test_m, calib, primary, floor, gate, leak)
    print(f"  churn proxy = severe revenue attrition (<0.70× trailing); this demo dataset "
          f"contains no household departures, so true attrition labels do not exist. "
          f"scale_pos_weight={spw:.1f}")
    entry = _save_and_register(
        "household-churn-xgb", model, cols, "XGBoost (XGBClassifier, hist, class-weighted)",
        "rev(t, t+6m] < 0.70 × rev(t-6m, t] — severe attrition proxy (no true churn in data)",
        "foundation sample: 360 households × 6 cuts; 83 positives",
        "temporal — train cuts 2024-08…2025-05, test cuts 2025-08 & 2025-11",
        train_m, test_m, calib, primary, floor, gate)
    _assert_anchors_intact()
    return entry


def train_agp_off_track() -> dict:
    frame = ds.build_agp_frame()
    df = frame.df
    cols = frame.feature_cols
    X = df[cols].to_numpy(float)
    y = df["label_off_track"].to_numpy(int)
    groups = df["advisor_id"].to_numpy()
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr_idx, te_idx = next(gss.split(X, y, groups))
    model = _fit(X[tr_idx], y[tr_idx])
    train_m = _metrics(y[tr_idx], model.predict_proba(X[tr_idx])[:, 1])
    ptest = model.predict_proba(X[te_idx])[:, 1]
    test_m = _metrics(y[te_idx], ptest)
    calib = _calibration_table(y[te_idx], ptest)
    floor, primary = 0.65, "roc_auc"
    leak = test_m["roc_auc"] > _LEAKAGE_AUC
    gate = (test_m[primary] >= floor) and not leak
    _print_block("AGP_OFF_TRACK_RISK (KPI measurement, group-by-advisor split)",
                 train_m, test_m, calib, primary, floor, gate, leak)
    print(f"  n_train={len(tr_idx)} n_test={len(te_idx)}; advisors disjoint across split; "
          f"attainment-derived columns EXCLUDED ({sorted(ds.AGP_EXCLUDED)}).")
    entry = _save_and_register(
        "agp-off-track-xgb", model, cols, "XGBoost (XGBClassifier, hist)",
        "measurement.status == 'OFF_TRACK' (single 2026-07-01 snapshot; learns co-occurring behaviors)",
        "foundation sample: 960 KPI measurements → advisor via edge traversal",
        "GroupShuffleSplit by advisor (80/20, seed 42) — no advisor spans both sides",
        train_m, test_m, calib, primary, floor, gate)
    _assert_anchors_intact()
    return entry
