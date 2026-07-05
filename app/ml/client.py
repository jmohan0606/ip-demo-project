from __future__ import annotations

"""ModelClient adapter (Section 11.1 §1).

Same house pattern as app/llm/client.py and app/graph/client.py: a Protocol, an error
type, implementations that keep all heavy-ML imports (sklearn / xgboost / torch / shap)
*inside* their methods, and a cached get_model_client() factory selected by
MODEL_CLIENT_MODE.

Two tiers:
  - deterministic  -> the current, verified scorers/vectors. NEVER deleted. This is the
                      fallback that guarantees `real` mode can never regress an endpoint.
  - real           -> trained artifacts loaded from the registry (§10). When no adequate
                      artifact exists for a request, raises ModelUnavailableError so the
                      caller falls back to the deterministic scorecard.

Nothing outside app/ml/real_client.py (+ app/ml/training/) may import xgboost/shap/torch.
"""

import math
import sqlite3
from pathlib import Path
from typing import Protocol, TypedDict

from app.config.settings import get_settings


class ModelClientError(RuntimeError):
    pass


class ModelUnavailableError(ModelClientError):
    """No adequate trained artifact for this request. Callers MUST catch this and fall
    back to the deterministic scorer — this is what keeps `real` mode >= today's behavior."""


class ModelScore(TypedDict):
    score: float               # 0-100, same scale as the scorecard
    confidence: float          # 0-1
    contributions: list[dict]  # {feature, value, points, why, direction} (§4)
    served_by: str             # e.g. "xgboost-revenue-decline-v1" | "scorecard"
    model_card_ref: str        # registry key
    methodology_patch: dict     # merged into the scorecard's methodology dict


class ModelClient(Protocol):
    """Adapter interface for the trained-model tier (Section 11.1)."""

    def score_risk(
        self, prediction_type: str, entity_type: str, entity_id: str, features: dict
    ) -> ModelScore: ...

    def forecast_series(
        self, entity_type: str, entity_id: str, series: list[dict], horizon: int = 6
    ) -> dict: ...

    def anomaly_scores(self, entity_type: str, rows: list[dict]) -> list[dict]: ...

    def entity_embedding(self, entity_type: str, entity_id: str) -> list[float] | None: ...

    def describe(self) -> dict: ...


# --------------------------------------------------------------------------------------
# Shared helpers (no heavy imports)
# --------------------------------------------------------------------------------------

def _read_latest_embedding(entity_type: str, entity_id: str) -> list[float] | None:
    """Read the newest persisted deterministic-projection vector for an entity from the
    existing embeddings SQLite table (app/embeddings/service.py). Read-only."""
    import json

    db_path = get_settings().sqlite_db_path
    if not Path(db_path).exists():
        return None
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT vector_json FROM embeddings WHERE entity_type=? AND entity_id=? "
                "ORDER BY generated_at DESC LIMIT 1",
                (entity_type.upper(), entity_id),
            ).fetchone()
    except sqlite3.OperationalError:
        return None
    if not row or not row[0]:
        return None
    try:
        vec = json.loads(row[0])
        return [float(x) for x in vec]
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _seasonal_naive_forecast(series: list[dict], horizon: int) -> dict:
    """Real arithmetic on real history: next values = same month one year ago when the
    series is long enough, else the last observed value. Uncertainty band from the
    empirical volatility (std) of the last 12 buckets. Honest and simple — no fabrication.
    """
    values = [float(p.get("value", p.get("actual", 0.0))) for p in series]
    months = [p.get("month") for p in series]
    if not values:
        return {"forecast": [], "model": {"served_by": "seasonal-naive-baseline", "note": "empty series"}}

    window = values[-12:] if len(values) >= 12 else values
    mean = sum(window) / len(window)
    var = sum((v - mean) ** 2 for v in window) / max(1, len(window))
    std = math.sqrt(var)

    def _next_month(m: str | None, step: int) -> str | None:
        if not m or "-" not in m:
            return None
        y, mm = m.split("-")[:2]
        total = int(y) * 12 + (int(mm) - 1) + step
        return f"{total // 12:04d}-{(total % 12) + 1:02d}"

    last_month = months[-1] if months else None
    out = []
    for h in range(1, horizon + 1):
        # seasonal: value 12 months before the target month, if present in history
        if len(values) >= 12:
            p50 = values[-12 + (h - 1)] if (h - 1) < 12 else values[-1]
        else:
            p50 = values[-1]
        out.append(
            {
                "month": _next_month(last_month, h),
                "p50": round(p50, 2),
                "p10": round(p50 - 1.2816 * std, 2),
                "p90": round(p50 + 1.2816 * std, 2),
            }
        )
    return {
        "forecast": out,
        "model": {
            "served_by": "seasonal-naive-baseline",
            "caveats": ["deterministic baseline — same-month-last-year with empirical volatility band"],
        },
    }


# --------------------------------------------------------------------------------------
# Deterministic tier — delegates to the current verified paths; never deleted
# --------------------------------------------------------------------------------------

class DeterministicModelClient:
    """The safe default. score_risk always raises ModelUnavailableError so the existing
    inline scorecard in PredictionService runs unchanged; forecast returns a labeled
    seasonal-naive baseline; anomaly_scores is not claimed in this mode; embeddings read
    the existing deterministic-projection vectors."""

    def score_risk(self, prediction_type, entity_type, entity_id, features) -> ModelScore:
        raise ModelUnavailableError(
            "MODEL_CLIENT_MODE=deterministic: risk scoring is served by the scorecard"
        )

    def forecast_series(self, entity_type, entity_id, series, horizon=6) -> dict:
        result = _seasonal_naive_forecast(series, horizon)
        result["entity_id"] = entity_id
        return result

    def anomaly_scores(self, entity_type, rows) -> list[dict]:
        return []

    def entity_embedding(self, entity_type, entity_id) -> list[float] | None:
        return _read_latest_embedding(entity_type, entity_id)

    def describe(self) -> dict:
        return {"mode": "deterministic", "tier": "verified-scorers", "serves_risk": False}


# --------------------------------------------------------------------------------------
# Real tier — loads trained artifacts via the registry. Skeleton in commit 1: with no
# trained models yet it correctly raises ModelUnavailableError everywhere, so the live
# endpoints stay on the deterministic scorecard until commit 3-4 train + wire real models.
# --------------------------------------------------------------------------------------

class RealModelClient:
    """Trained-model tier. Heavy imports (xgboost/shap/torch) happen lazily inside the
    concrete scoring methods, added in commits 3-4. Until an adequate artifact is present
    and passes its quality gate (registry.serves()), every method raises
    ModelUnavailableError — real mode is therefore never worse than deterministic."""

    def score_risk(self, prediction_type, entity_type, entity_id, features) -> ModelScore:
        # Full implementation lands in commit 4 (RealModelClient.score_risk + SHAP mapping).
        from app.ml import registry

        model_name = _RISK_MODEL_BY_TYPE.get(prediction_type)
        if not model_name or not registry.serves(model_name):
            raise ModelUnavailableError(
                f"no serving artifact for {prediction_type} (registry gate not passed)"
            )
        # Delegated to the trained-model implementation (added commit 4).
        from app.ml.real_scoring import score_risk as _score

        return _score(model_name, prediction_type, entity_type, entity_id, features)

    def forecast_series(self, entity_type, entity_id, series, horizon=6) -> dict:
        from app.ml import registry

        if not registry.serves("revenue-forecast-gru"):
            # fall back to the honest deterministic baseline
            return DeterministicModelClient().forecast_series(entity_type, entity_id, series, horizon)
        from app.ml.real_forecast import forecast_series as _fc

        return _fc(entity_type, entity_id, series, horizon)

    def anomaly_scores(self, entity_type, rows) -> list[dict]:
        from app.ml import registry

        if not registry.serves("activity-anomaly-iforest"):
            return []
        from app.ml.real_anomaly import anomaly_scores as _an

        return _an(entity_type, rows)

    def entity_embedding(self, entity_type, entity_id) -> list[float] | None:
        # In real mode, prefer registered GNN embeddings when present (§7/§8); otherwise
        # fall back to the existing deterministic-projection vectors.
        return _read_latest_embedding(entity_type, entity_id)

    def describe(self) -> dict:
        from app.ml import registry

        entries = registry.list_entries()
        return {
            "mode": "real",
            "tier": "trained-artifacts",
            "registered_models": [e.get("name") for e in entries],
            "serving": [e.get("name") for e in entries if e.get("quality_gate") == "passed"],
        }


# Maps a prediction_type string to its registry model name (populated as models land).
_RISK_MODEL_BY_TYPE = {
    "REVENUE_DECLINE_RISK": "revenue-decline-xgb",
    "AGP_OFF_TRACK_RISK": "agp-off-track-xgb",
    "HOUSEHOLD_CHURN_PROPENSITY": "household-churn-xgb",
}


_model_client: ModelClient | None = None


def get_model_client() -> ModelClient:
    """Select the ModelClient per MODEL_CLIENT_MODE (deterministic | real)."""
    global _model_client
    if _model_client is None:
        mode = getattr(get_settings(), "model_client_mode", "deterministic").lower()
        if mode == "deterministic":
            _model_client = DeterministicModelClient()
        elif mode == "real":
            _model_client = RealModelClient()
        else:
            raise ModelClientError(
                f"Unknown MODEL_CLIENT_MODE '{mode}' (expected deterministic|real)"
            )
    return _model_client


def reset_model_client() -> None:
    global _model_client
    _model_client = None
