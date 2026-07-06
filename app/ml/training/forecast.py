from __future__ import annotations

"""Train the revenue-forecast GRU (Section 11.1 §5).

Shared 1-layer GRU over all 60 advisor monthly series (36 months). Trains next-step on
months 0–29, validates a 6-month autoregressive rollout on months 30–35 against TWO
mandatory baselines (seasonal-naive, 3-month MA). Serves only if it beats seasonal-naive
(else the deterministic seasonal-naive baseline serves — honest by construction). The band
is empirical per-horizon validation-residual quantiles. Time-boxed for the 2-core box.
"""

import datetime as _dt
import hashlib
import math
import time

import numpy as np
import torch
from torch import nn

from app.config.settings import get_settings
from app.ml import registry
from app.ml.real_forecast import FORECAST_MODEL, GRUForecaster, _month_feats
from app.ml.training import datasets as ds

TRAIN_MONTHS = 30  # train on 0..29, validate 30..35
HORIZON = 6
SEED = 42


def _smape(actual: np.ndarray, pred: np.ndarray) -> float:
    denom = np.abs(actual) + np.abs(pred) + 1e-9
    return float(np.mean(2 * np.abs(actual - pred) / denom))


def train_revenue_forecast() -> dict:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    labels, series = ds.monthly_revenue_series()
    advisors = sorted(series)
    revs = {a: np.asarray(series[a], dtype=float) for a in advisors}
    n_months = len(labels)
    if n_months < TRAIN_MONTHS + HORIZON:
        raise RuntimeError(f"need >= {TRAIN_MONTHS + HORIZON} months, have {n_months}")

    # per-advisor normalization from the training region only
    stats, Z = {}, {}
    for a in advisors:
        logs = np.log1p(np.clip(revs[a], 0, None))
        mean = float(logs[:TRAIN_MONTHS].mean())
        std = float(logs[:TRAIN_MONTHS].std()) or 1.0
        stats[a] = {"mean": mean, "std": std}
        Z[a] = (logs - mean) / std

    mfeat = np.asarray([_month_feats(l) for l in labels], dtype=float)  # (n_months, 2)

    # training tensors: input months 0..TRAIN_MONTHS-1, predict next-step
    X, Y = [], []
    for a in advisors:
        feats = np.column_stack([Z[a][:TRAIN_MONTHS], mfeat[:TRAIN_MONTHS]])  # (30,3)
        X.append(feats)
        Y.append(Z[a][1:TRAIN_MONTHS + 1])  # next-step targets (30,)
    X = torch.tensor(np.stack(X), dtype=torch.float32)
    Y = torch.tensor(np.stack(Y), dtype=torch.float32)

    hidden = 32
    model = GRUForecaster(hidden=hidden)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.MSELoss()
    cap_s = get_settings().ml_time_box_minutes * 60
    t0 = time.time()
    best, best_state, patience = float("inf"), None, 0
    epochs_run = 0
    for epoch in range(200):
        model.train()
        opt.zero_grad()
        loss = loss_fn(model(X), Y)
        loss.backward()
        opt.step()
        epochs_run = epoch + 1
        if loss.item() < best - 1e-5:
            best, best_state, patience = loss.item(), {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            patience += 1
        if patience >= 20 or (time.time() - t0) > cap_s:
            break
    if best_state:
        model.load_state_dict(best_state)
    model.eval()

    # validation: 6-month autoregressive rollout from month 30, per advisor
    resid = {h: [] for h in range(HORIZON)}
    gru_a, gru_p, sn_a, sn_p, ma_a, ma_p = [], [], [], [], [], []
    with torch.no_grad():
        for a in advisors:
            z = list(Z[a][:TRAIN_MONTHS])
            seq_lab = list(labels[:TRAIN_MONTHS])
            for h in range(HORIZON):
                feats = [[z[i], *_month_feats(seq_lab[i])] for i in range(len(z))]
                zt = float(model(torch.tensor([feats], dtype=torch.float32))[0, -1].item())
                nxt = labels[TRAIN_MONTHS + h]
                pred_rev = math.expm1(zt * stats[a]["std"] + stats[a]["mean"])
                actual_rev = revs[a][TRAIN_MONTHS + h]
                resid[h].append(actual_rev - pred_rev)
                gru_a.append(actual_rev); gru_p.append(max(pred_rev, 0.0))
                # seasonal-naive: same month last year
                sn_a.append(actual_rev); sn_p.append(revs[a][TRAIN_MONTHS + h - 12])
                # 3-month MA over actual trailing
                ma_a.append(actual_rev); ma_p.append(float(revs[a][TRAIN_MONTHS + h - 3:TRAIN_MONTHS + h].mean()))
                z.append(zt); seq_lab.append(nxt)

    gru_smape = _smape(np.array(gru_a), np.array(gru_p))
    sn_smape = _smape(np.array(sn_a), np.array(sn_p))
    ma_smape = _smape(np.array(ma_a), np.array(ma_p))
    residual_quantiles = {
        str(h): {"p10": float(np.quantile(resid[h], 0.10)), "p90": float(np.quantile(resid[h], 0.90))}
        for h in range(HORIZON)
    }
    beats = gru_smape <= sn_smape
    served_by = FORECAST_MODEL if beats else "seasonal-naive-baseline"

    print("=" * 72)
    print("REVENUE FORECAST GRU (60 advisor series × 36 months)")
    print("=" * 72)
    print(f"  epochs={epochs_run}  train_mse={best:.5f}  wall={time.time()-t0:.1f}s  hidden={hidden}")
    print(f"  val sMAPE:  GRU={gru_smape:.4f}   seasonal_naive={sn_smape:.4f}   ma3={ma_smape:.4f}")
    print(f"  beats seasonal-naive: {beats} -> served_by={served_by}, gate={'passed' if beats else 'failed'}")

    now = _dt.datetime.now().strftime("%Y-%m-%d")
    art = registry.artifact_dir() / f"{FORECAST_MODEL}.pt"
    torch.save({"state_dict": model.state_dict(), "hidden": hidden, "advisor_stats": stats,
                "residual_quantiles": residual_quantiles, "trained_at": now}, art)
    sha = hashlib.sha256(art.read_bytes()).hexdigest()[:16]
    entry = {
        "name": FORECAST_MODEL, "version": "1.0", "algorithm": "GRU (1-layer, hidden 32) · shared across advisors",
        "training_date": now,
        "training_data": "60 advisor monthly revenue series × 36 months (2023-08…2026-07)",
        "label_definition": "next-month revenue (self-supervised next-step); 6-mo autoregressive rollout",
        "split": "train months 0-29, validate 6-month rollout on months 30-35",
        "metrics": {"gru_smape": round(gru_smape, 4), "seasonal_naive_smape": round(sn_smape, 4),
                    "ma3_smape": round(ma_smape, 4), "epochs": epochs_run},
        "primary_metric": "gru_smape", "primary_metric_value": round(gru_smape, 4),
        "quality_floor": round(sn_smape, 4),
        "features": ["log1p(revenue) z-score", "sin(month)", "cos(month)"],
        "caveats": "60 series × 36 months — demo scale; band = empirical validation-residual quantiles.",
        "artifact_path": str(art), "artifact_sha256": sha,
        "served_by": served_by,
        "quality_gate": "passed" if beats else "failed",
        "served_since": now if beats else None,
    }
    registry.upsert_entry(entry)
    return entry


if __name__ == "__main__":
    train_revenue_forecast()
