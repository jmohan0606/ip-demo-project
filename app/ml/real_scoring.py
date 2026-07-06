from __future__ import annotations

"""Real-tier risk scoring (Section 11.1 §3.5 + §4).

Loads a trained XGBoost artifact and produces a ModelScore in the EXACT shape the live
PredictionService/frontend already consume ({feature, value, points, why} + additive
`direction`), so promoting the model changes depth, not schema.

REVENUE_DECLINE_RISK is trained at household level; the advisor score is the revenue-
weighted mean of per-household P(decline), and contributions are the revenue-weighted mean
of per-household TreeSHAP values, mapped to an additive 0-100 point decomposition
(score ≈ base_value + Σ signed_points).

Heavy imports (xgboost via joblib, shap) are local to this module — business code reaches
it only through app.ml.client.RealModelClient.
"""

import math

import joblib
import numpy as np

from app.ml import registry
from app.ml.client import ModelUnavailableError
from app.ml.training import datasets as ds

_TOP_N = 8


def _load(model_name: str):
    entry = registry.get_entry(model_name)
    if not entry:
        raise ModelUnavailableError(f"no registry entry for {model_name}")
    payload = joblib.load(entry["artifact_path"])
    return payload["model"], payload["feature_cols"], entry


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _friendly(feature: str) -> str:
    return feature.replace("_", " ")


def _contributions_from_shap(feature_cols, mean_value, mean_phi_margin, score, base_score) -> list[dict]:
    """Map revenue-weighted mean margin-SHAP into an additive 0-100 point decomposition:
    signed_points allocate (score - base_score) in proportion to each feature's mean SHAP,
    so Σ signed_points == score - base_score exactly (the additivity identity, §4)."""
    total_phi = float(np.sum(mean_phi_margin))
    span = score - base_score
    k = (span / total_phi) if abs(total_phi) > 1e-9 else 0.0
    signed = k * np.asarray(mean_phi_margin, dtype=float)
    items = []
    for i, feat in enumerate(feature_cols):
        pts = float(signed[i])
        items.append({
            "feature": feat,
            "value": round(float(mean_value[i]), 4),
            "points": round(abs(pts), 1),
            "direction": 1 if pts > 0 else -1,
            "_signed": pts,
            "why": (f"{'raises' if pts > 0 else 'reduces'} decline risk by "
                    f"{abs(pts):.1f} points ({_friendly(feat)})"),
        })
    items.sort(key=lambda c: abs(c["_signed"]), reverse=True)
    top = items[:_TOP_N]
    rest = items[_TOP_N:]
    if rest:
        rem = sum(c["_signed"] for c in rest)
        top.append({
            "feature": "other_features", "value": None, "points": round(abs(rem), 1),
            "direction": 1 if rem > 0 else -1, "_signed": rem,
            "why": f"combined effect of {len(rest)} smaller features",
        })
    for c in top:
        c.pop("_signed", None)
    return top


def _score_revenue_decline(entity_id: str, model_name: str) -> dict:
    import shap

    model, feature_cols, entry = _load(model_name)
    X, weights = ds.build_current_household_features(entity_id)
    if X.empty or float(weights.sum()) <= 0:
        raise ModelUnavailableError(f"no household features for {entity_id}")
    X = X[feature_cols]
    w = weights.to_numpy(float)
    w = w / w.sum()

    proba = model.predict_proba(X.to_numpy(float))[:, 1]
    score = round(float(np.dot(w, proba) * 100.0), 1)
    confidence = round(min(0.95, max(0.5, float(np.dot(w, np.abs(proba - 0.5) * 2)))), 2)

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X.to_numpy(float))  # (n_hh, n_feat) margin space
    if isinstance(sv, list):  # some shap versions return per-class list
        sv = sv[1]
    mean_phi = np.average(sv, axis=0, weights=w)
    mean_value = np.average(X.to_numpy(float), axis=0, weights=w)
    base_margin = float(np.ravel(explainer.expected_value)[-1])
    base_score = round(_sigmoid(base_margin) * 100.0, 1)

    contributions = _contributions_from_shap(feature_cols, mean_value, mean_phi, score, base_score)
    m = entry.get("metrics", {}).get("test", {})
    methodology_patch = {
        "model_name": "Revenue Decline · XGBoost",
        "model_family": "Gradient-boosted trees (XGBoost) · household-level, revenue-weighted to advisor · TreeSHAP attribution",
        "model_version": entry.get("version", "1.0"),
        "served_by": f"{model_name} v{entry.get('version', '1.0')}",
        "trained_alternative": "iPerform Risk Scorecard (deterministic fallback when the model's quality gate is not met)",
        "pipeline": [
            "Build leakage-safe features for each of the advisor's households as of the latest data month",
            "Predict P(6-month revenue decline) per household with the trained XGBoost model",
            "Aggregate to advisor: revenue-weighted mean probability → 0-100 risk score",
            "Attribute with TreeSHAP: revenue-weighted mean SHAP per feature → additive signed points",
            "Band score → severity; derive confidence from the prediction margin",
            "Persist score + contributions + reasoning trace (same artifact chain as the scorecard)",
        ],
        "features_used": [c["feature"] for c in contributions],
        "score_formula": "risk = 100 · Σ_h w_h·P(decline_h) / Σ_h w_h,   w_h = household trailing-6m revenue",
        "base_value": base_score,
        "additivity": "score ≈ base_value + Σ signed_points (TreeSHAP, revenue-weighted)",
        "households_scored": int(len(X)),
        "training_metrics": {"roc_auc": m.get("roc_auc"), "pr_auc": m.get("pr_auc"), "test_n": m.get("n")},
        "caveats": entry.get("caveats"),
        "computed_score": score,
    }
    return {
        "score": score, "confidence": confidence, "contributions": contributions,
        "served_by": methodology_patch["served_by"], "model_card_ref": model_name,
        "methodology_patch": methodology_patch,
        "explanation": (
            f"XGBoost revenue-decline model: {score}/100 risk, revenue-weighted across "
            f"{len(X)} households (base {base_score}). Real TreeSHAP attribution; "
            f"held-out ROC-AUC {m.get('roc_auc')}."
        ),
    }


def score_risk(model_name: str, prediction_type: str, entity_type: str, entity_id: str,
               features: dict) -> dict:
    if prediction_type == "REVENUE_DECLINE_RISK":
        return _score_revenue_decline(entity_id, model_name)
    # AGP is trained but currently below its quality gate, so RealModelClient never routes
    # here for it; other types are not modelled yet.
    raise ModelUnavailableError(f"real scoring not implemented for {prediction_type}")
