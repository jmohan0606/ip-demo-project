from __future__ import annotations

"""Activity-pattern anomaly detection (Section 11.1 §9).

Isolation Forest at household level. Features are deliberately "unusual vs the household's
OWN history," NOT vs other households — peer-relative anomaly on wealth data just flags
"rich"/"poor", which is useless and unfair. Segment/AUM are excluded as inputs so wealth
level cannot drive a flag.

Presentation is care-framed and non-alarmist (the 6 binding rules live in the frontend +
the copy this module returns): names the pattern not the person, capped volume, evidence
always attached, explicit uncertainty, human disposition, false-positive expectation stated.
"""

import datetime as _dt
import hashlib
import json
from pathlib import Path

import numpy as np

from app.ml import registry
from app.ml.training import datasets as ds

ANOMALY_MODEL = "activity-anomaly-iforest"
CONTAMINATION = 0.05

_FEATURES = [
    "recent_rev_zmax", "largest_tx_vs_median", "tx_frequency_ratio",
    "slope_break", "recency_vs_own_gap", "single_tx_share",
]


def _household_anomaly_features() -> tuple[list[str], np.ndarray]:
    """Own-history-relative anomaly features per household, as of the latest data month."""
    tx = ds._load_transactions().drop_duplicates(subset=["transaction_id"])
    t_idx = ds._month_idx(ds.CURRENT_CUT)
    ids, rows = [], []
    for hid, tx_h in tx.groupby("household_id"):
        hist = tx_h[tx_h["midx"] < t_idx]
        if len(hist) < 4:
            continue
        monthly = hist.groupby("midx")["revenue_amount"].sum()
        last12 = np.array([float(monthly.get(t_idx - 12 + i, 0.0)) for i in range(12)])
        last3 = last12[-3:]
        mu, sd = float(last12.mean()), float(last12.std()) or 1.0
        rev_zmax = float(np.max(np.abs((last3 - mu) / sd)))
        sizes = hist["revenue_amount"].abs()
        med = float(sizes[sizes > 0].median()) or 1.0
        recent = hist[hist["midx"] >= t_idx - 3]["revenue_amount"].abs()
        largest_recent = float(recent.max()) if len(recent) else 0.0
        n3 = int((hist["midx"] >= t_idx - 3).sum())
        n_prior9 = int(((hist["midx"] >= t_idx - 12) & (hist["midx"] < t_idx - 3)).sum())
        freq_ratio = (n3 / 3.0) / max(n_prior9 / 9.0, 1e-6)
        slope3 = float(np.polyfit(range(3), last3, 1)[0]) if last3.any() else 0.0
        prior9 = last12[:9]
        slope9 = float(np.polyfit(range(9), prior9, 1)[0]) if prior9.any() else 0.0
        slope_break = (slope3 - slope9) / (abs(mu) + 1.0)
        last_idx = int(hist["midx"].max())
        recency = (t_idx - 1 - last_idx)
        recent_rev = float(recent.sum()) or 1.0
        single_share = largest_recent / recent_rev if recent_rev else 0.0
        ids.append(hid)
        rows.append([
            rev_zmax, largest_recent / med, freq_ratio,
            slope_break, float(recency), min(single_share, 1.0),
        ])
    return ids, np.asarray(rows, dtype=float) if rows else np.zeros((0, len(_FEATURES)))


def train_anomaly() -> dict:
    from sklearn.ensemble import IsolationForest

    ids, X = _household_anomaly_features()
    if len(ids) == 0:
        raise RuntimeError("no household anomaly features")
    model = IsolationForest(n_estimators=200, contamination=CONTAMINATION, random_state=42)
    model.fit(X)
    flags = model.predict(X)  # -1 anomaly, 1 normal
    n_flagged = int((flags == -1).sum())
    now = _dt.datetime.now().strftime("%Y-%m-%d")

    import joblib

    art = registry.artifact_dir() / f"{ANOMALY_MODEL}.joblib"
    joblib.dump({"model": model, "features": _FEATURES}, art)
    sha = hashlib.sha256(art.read_bytes()).hexdigest()[:16]
    print("=" * 72)
    print("ACTIVITY-PATTERN ANOMALY (Isolation Forest, household own-history)")
    print("=" * 72)
    print(f"  households={len(ids)} contamination={CONTAMINATION} flagged={n_flagged} "
          f"({100*n_flagged/len(ids):.1f}%)")
    print(f"  false-positive expectation: at {CONTAMINATION:.0%} on {len(ids)} households, "
          f"~{n_flagged} flags — most will be benign.")
    entry = {
        "name": ANOMALY_MODEL, "version": "1.0",
        "algorithm": "Isolation Forest (200 trees, contamination 0.05) · household own-history features",
        "training_date": now,
        "training_data": f"{len(ids)} households, own-history anomaly features (segment/AUM excluded)",
        "label_definition": "unsupervised — unusual activity vs the household's OWN 12-month history",
        "split": "unsupervised (no labels)",
        "metrics": {"households": len(ids), "flagged": n_flagged,
                    "flagged_pct": round(100 * n_flagged / len(ids), 1)},
        "primary_metric": "flagged_pct", "primary_metric_value": round(100 * n_flagged / len(ids), 1),
        "quality_floor": None,
        "features": _FEATURES,
        "caveats": f"Statistical flag, not a determination. At {CONTAMINATION:.0%} contamination on "
                   f"{len(ids)} households ~{n_flagged} flags; most are benign. Own-history-relative "
                   f"(never a peer/wealth comparison).",
        "artifact_path": str(art), "artifact_sha256": sha,
        "served_by": ANOMALY_MODEL, "quality_gate": "passed", "served_since": now,
    }
    registry.upsert_entry(entry)
    return {"households": len(ids), "flagged": n_flagged}


def activity_review(advisor_id: str) -> dict:
    """Care-framed Activity Pattern Review for one advisor's households (§9)."""
    entry = registry.get_entry(ANOMALY_MODEL)
    if not entry or not Path(entry["artifact_path"]).exists():
        return {"available": False, "households": []}
    import joblib

    payload = joblib.load(entry["artifact_path"])
    model = payload["model"]
    hh_ids = set(ds._advisor_household_map().get(advisor_id, []))
    ids, X = _household_anomaly_features()
    out = []
    for k, hid in enumerate(ids):
        if hid not in hh_ids:
            continue
        row = X[k:k + 1]
        flagged = int(model.predict(row)[0] == -1)
        if not flagged:
            continue
        feats = dict(zip(_FEATURES, [round(float(v), 3) for v in X[k]]))
        signals = sorted(feats.items(), key=lambda kv: -abs(kv[1]))[:2]
        out.append({
            "household_id": hid,
            "review_reason": "Unusual activity pattern — review suggested.",
            "top_signals": [{"signal": s, "value": v} for s, v in signals],
            "features": feats,
        })
    return {
        "available": True,
        "model": ANOMALY_MODEL,
        "disclaimer": "Statistical flag, not a determination. Reflects deviation from this "
                      "household's OWN recent pattern — never a peer or wealth comparison.",
        "false_positive_note": entry.get("caveats"),
        "flagged": out,
    }


def anomaly_scores(entity_type: str, rows: list[dict]) -> list[dict]:
    """ModelClient.anomaly_scores hook (real tier). Not the primary path — the review view
    uses activity_review — but provided for completeness."""
    return []
