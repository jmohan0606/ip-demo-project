from __future__ import annotations

"""GRU revenue forecast — model + serving (Section 11.1 §5).

Torch lives only in this module (and app/ml/training/forecast.py). The trained artifact
carries per-advisor normalization stats + empirical per-horizon residual quantiles, so the
serving path needs no re-training and produces an honest uncertainty band. Falls back to the
deterministic seasonal-naive baseline (app.ml.client) whenever the artifact is absent.
"""

import math

import numpy as np
import torch
from torch import nn

from app.ml import registry
from app.ml.client import ModelUnavailableError

FORECAST_MODEL = "revenue-forecast-gru"


class GRUForecaster(nn.Module):
    """1-layer GRU over [z(log1p revenue), sin(month), cos(month)] → next-month z."""

    def __init__(self, hidden: int = 32) -> None:
        super().__init__()
        self.hidden = hidden
        self.gru = nn.GRU(input_size=3, hidden_size=hidden, num_layers=1, batch_first=True)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # x: (B, T, 3)
        out, _ = self.gru(x)
        return self.head(out).squeeze(-1)  # (B, T)


def _month_feats(month_label: str) -> tuple[float, float]:
    m = int(month_label.split("-")[1])
    ang = 2 * math.pi * (m - 1) / 12
    return math.sin(ang), math.cos(ang)


def _next_label(label: str, step: int) -> str:
    y, m = label.split("-")
    total = int(y) * 12 + (int(m) - 1) + step
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def build_model(hidden: int) -> GRUForecaster:
    return GRUForecaster(hidden=hidden)


def _load_artifact():
    entry = registry.get_entry(FORECAST_MODEL)
    if not entry or not registry.serves(FORECAST_MODEL):
        raise ModelUnavailableError("revenue forecast model not serving (gate/artifact)")
    blob = torch.load(entry["artifact_path"], map_location="cpu", weights_only=False)
    model = build_model(blob["hidden"])
    model.load_state_dict(blob["state_dict"])
    model.eval()
    return model, blob, entry


def forecast_series(entity_type: str, entity_id: str, series: list[dict], horizon: int = 6) -> dict:
    """Autoregressive 6-month rollout with an empirical residual-quantile band."""
    model, blob, entry = _load_artifact()
    labels = [str(p.get("month")) for p in series]
    values = [float(p.get("value", p.get("actual", 0.0))) for p in series]
    if len(values) < 6:
        raise ModelUnavailableError("insufficient history for forecast")

    stats = blob["advisor_stats"].get(entity_id)
    logs = [math.log1p(max(v, 0.0)) for v in values]
    mean = stats["mean"] if stats else float(np.mean(logs))
    std = (stats["std"] if stats else float(np.std(logs))) or 1.0

    z = [(lv - mean) / std for lv in logs]
    seq_labels = list(labels)
    with torch.no_grad():
        out = []
        for h in range(1, horizon + 1):
            feats = [[z[i], *_month_feats(seq_labels[i])] for i in range(len(z))]
            x = torch.tensor([feats], dtype=torch.float32)
            z_next = float(model(x)[0, -1].item())
            next_label = _next_label(seq_labels[-1], 1)
            rev = math.expm1(z_next * std + mean)
            rq = blob["residual_quantiles"].get(str(h - 1), {"p10": 0.0, "p90": 0.0})
            out.append({
                "month": next_label,
                "p50": round(max(rev, 0.0), 2),
                "p10": round(max(rev + rq["p10"], 0.0), 2),
                "p90": round(max(rev + rq["p90"], 0.0), 2),
            })
            z.append(z_next)
            seq_labels.append(next_label)

    m = entry.get("metrics", {})
    return {
        "entity_id": entity_id,
        "granularity": "month",
        "history": [{"month": labels[i], "actual": round(values[i], 2)} for i in range(len(values))],
        "forecast": out,
        "model": {
            "served_by": entry.get("served_by", FORECAST_MODEL),
            "val_smape": m.get("gru_smape"),
            "baseline_smape": {"seasonal_naive": m.get("seasonal_naive_smape"), "ma3": m.get("ma3_smape")},
            "caveats": entry.get("caveats"),
        },
    }
