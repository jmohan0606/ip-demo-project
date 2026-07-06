"""Before/after contribution verification (Section 11.1 §4).

Proves the model promotion is real and schema-safe:
  - BEFORE (endpoint): deterministic scorecard contributions for A001 + A020.
  - AFTER  (endpoint): real-label XGBoost TreeSHAP contributions for the same advisors.
  - REFERENCE: the retired synthetic-label RandomForest's feature importances (captured
    once, while app/prediction/prediction_engine.py still exists; the script degrades
    gracefully after that module is deleted).
Asserts the response JSON schema is unchanged between modes and that two advisors get
different real-mode scores. Saves raw output to docs/section11/evidence/.
"""
import json
import os
from pathlib import Path

ADVISORS = ["A001", "A020"]
EVIDENCE = Path("docs/section11/evidence")
REQUIRED_KEYS = {"prediction_id", "prediction_type", "score", "risk_band", "confidence",
                 "contributions", "feature_snapshot_id", "explanation", "methodology"}


def _predict(advisor: str) -> dict:
    from app.ml.client import reset_model_client
    from app.prediction.service import PredictionService
    reset_model_client()
    return PredictionService().predict_revenue_decline(advisor, persist=False)


def _run_mode(mode: str) -> dict:
    os.environ["MODEL_CLIENT_MODE"] = mode
    from app.config.settings import get_settings
    get_settings.cache_clear()
    return {a: _predict(a) for a in ADVISORS}


def _synthetic_reference() -> dict:
    """The retired synthetic-label RF's top feature importances for A001 (historical
    reference). Optional — skipped if the dormant module has been deleted."""
    try:
        from app.prediction.feature_matrix_builder import FeatureMatrixBuilder
        from app.prediction.prediction_engine import LocalPredictionEngine
        from app.models.predictions import PredictionType
    except Exception as exc:  # module retired
        return {"available": False, "note": f"dormant synthetic-label engine retired ({exc})"}
    df = FeatureMatrixBuilder().advisor_matrix()
    engine = LocalPredictionEngine()
    _, meta = engine.predict(df, PredictionType.REVENUE_GROWTH)
    return {"available": True, "model": engine.model_name,
            "training_target": "synthetic rank-heuristic (_synthetic_target)", "metadata": meta}


def _table(contribs: list[dict]) -> list[str]:
    out = []
    for c in contribs:
        d = c.get("direction")
        arrow = "" if d is None else ("↑" if d > 0 else "↓")
        out.append(f"    {c['feature']:34} pts={c['points']:>6} {arrow}  value={c.get('value')}")
    return out


if __name__ == "__main__":
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    before = _run_mode("deterministic")
    after = _run_mode("real")
    ref = _synthetic_reference()

    print("=" * 78)
    print("BEFORE/AFTER CONTRIBUTIONS — REVENUE_DECLINE_RISK")
    print("=" * 78)
    for a in ADVISORS:
        b, af = before[a], after[a]
        print(f"\n--- {a} ---")
        print(f"  BEFORE served_by={b['methodology'].get('served_by')} score={b['score']} conf={b['confidence']}")
        print("\n".join(_table(b["contributions"])))
        print(f"  AFTER  served_by={af['methodology'].get('served_by')} score={af['score']} conf={af['confidence']} "
              f"base={af['methodology'].get('base_value')}")
        print("\n".join(_table(af["contributions"])))

    # schema assertion
    for a in ADVISORS:
        assert REQUIRED_KEYS <= set(before[a]), f"before {a} missing keys"
        assert REQUIRED_KEYS <= set(after[a]), f"after {a} missing keys"
    # real mode actually served the model
    assert after["A001"]["methodology"].get("served_by", "").startswith("revenue-decline-xgb"), \
        "real mode did not serve the XGBoost model"
    # two advisors differ in real mode
    assert after["A001"]["score"] != after["A020"]["score"], "real-mode scores identical across advisors"
    print(f"\nSchema unchanged between modes: PASS")
    print(f"Real mode served the model: PASS (A001={after['A001']['score']} vs A020={after['A020']['score']})")
    print(f"Synthetic-label reference: {'captured' if ref.get('available') else ref.get('note')}")

    out = {"before": before, "after": after, "synthetic_reference": ref}
    (EVIDENCE / "contributions_before_after.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved -> {EVIDENCE / 'contributions_before_after.json'}")
    os.environ["MODEL_CLIENT_MODE"] = "deterministic"
