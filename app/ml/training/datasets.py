from __future__ import annotations

"""Real-label training datasets (Section 11.1 §3).

Builds supervised frames at the HOUSEHOLD × as-of-date level (per the honest small-data
rule — 60 advisors is not a training set; ~2.2K household-period rows is). Advisor-level
scores are aggregations of household predictions, not a 60-row fit.

All reads are READ-ONLY over the foundation sample CSVs — no upserts, no mutation of any
persisted/anchored figure. Heavy modelling libs are NOT imported here; this module only
uses pandas/numpy to shape data + labels.

Label definitions (exact, §3.1), measured prevalence in parentheses (Fable §0):
  REVENUE_DECLINE_RISK   : rev(t, t+6m] < 0.85 * rev(t-6m, t]   (~26.6% of n≈2159)
  HOUSEHOLD_CHURN        : rev(t, t+6m] < 0.70 * rev(t-6m, t]   (~3.8%, severe attrition proxy)
  AGP_OFF_TRACK_RISK     : measurement.status == "OFF_TRACK"     (64% of 960 KPI rows)

Anti-leakage (§3.3): every feature uses only facts dated <= cut t; every label uses the
(t, t+6m] window only. The AGP model excludes attainment-derived columns (status is
computed from attainment_pct).
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

SAMPLE_DIR = Path("docs/tigergraph_foundation/data/sample")

# As-of cut points: each leaves a full 6-month label window (<= 2026-07) and >=12 months
# of prior history (data starts 2023-08).
CUT_POINTS = ["2024-08", "2024-11", "2025-02", "2025-05", "2025-08", "2025-11"]
ACTIVITY_FLOOR = 500.0  # prior-6m revenue floor to exclude dormant/noise households

DECLINE_THRESHOLD = 0.85  # <15% of trailing = decline
CHURN_THRESHOLD = 0.70    # <30% drop = severe-attrition churn proxy

# Feature columns the household risk models train on (labels + raw next-window revenue
# are deliberately NOT in this list — anti-leakage rule 2).
HOUSEHOLD_FEATURES = [
    "rev_trailing_3m", "rev_trailing_6m", "rev_trailing_12m",
    "rev_slope_6m", "rev_volatility_12m", "months_since_peak",
    "tx_count_3m", "tx_count_6m",
    "mean_tx_size_6m_ratio", "max_tx_size_6m_ratio",
    "product_count", "product_diversification",
    "account_count", "total_aum", "days_since_last_tx",
    "seg_HNW", "seg_AFFLUENT", "risk_conservative", "risk_moderate", "risk_aggressive",
]

# AGP model excludes any attainment-/status-derived column (status is a deterministic
# function of attainment_pct — including any of these would leak the label).
AGP_EXCLUDED = {
    "attainment_pct", "actual_value", "milestone_attainment_pct",
    "kpi_on_track_ratio", "agp_risk_score", "revenue_at_risk_estimate",
}


def _month_idx(ym: str) -> int:
    y, m = ym.split("-")[:2]
    return int(y) * 12 + (int(m) - 1)


def _to_ym(date_str: str) -> str:
    return date_str[:7]


@lru_cache(maxsize=1)
def _load_transactions() -> pd.DataFrame:
    """Revenue transactions joined to their household, with a month index. Cached."""
    tx = pd.read_csv(SAMPLE_DIR / "vertices" / "phx_dm_revenue_transaction.csv")
    link = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_transaction_for_household.csv")
    prod = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_transaction_for_product.csv")
    tx = tx.merge(link.rename(columns={"from_id": "transaction_id", "to_id": "household_id"}),
                  on="transaction_id", how="inner")
    tx = tx.merge(prod.rename(columns={"from_id": "transaction_id", "to_id": "product_id"}),
                  on="transaction_id", how="left")
    tx["revenue_amount"] = pd.to_numeric(tx["revenue_amount"], errors="coerce").fillna(0.0)
    tx["ym"] = tx["transaction_date"].astype(str).str[:7]
    tx["midx"] = tx["ym"].map(_month_idx)
    return tx


@lru_cache(maxsize=1)
def _load_households() -> pd.DataFrame:
    hh = pd.read_csv(SAMPLE_DIR / "vertices" / "phx_dm_household.csv")
    hh["total_aum"] = pd.to_numeric(hh["total_aum"], errors="coerce").fillna(0.0)
    accts = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_household_owns_account.csv")
    acct_count = accts.groupby("from_id").size().rename("account_count")
    hh = hh.merge(acct_count, left_on="household_id", right_index=True, how="left")
    hh["account_count"] = hh["account_count"].fillna(0).astype(int)
    return hh


def _window_revenue(tx_h: pd.DataFrame, lo_idx: int, hi_idx: int) -> float:
    """Sum revenue for month indices in [lo_idx, hi_idx] (inclusive)."""
    m = (tx_h["midx"] >= lo_idx) & (tx_h["midx"] <= hi_idx)
    return float(tx_h.loc[m, "revenue_amount"].sum())


def _ols_slope(y: list[float]) -> float:
    if len(y) < 2:
        return 0.0
    x = np.arange(len(y), dtype=float)
    xm, ym = x.mean(), float(np.mean(y))
    denom = float(((x - xm) ** 2).sum())
    if denom == 0:
        return 0.0
    return float((((x - xm) * (np.array(y) - ym)).sum()) / denom)


@dataclass
class HouseholdFrame:
    df: pd.DataFrame          # one row per (household, cut) passing the activity floor
    feature_cols: list[str]


def _household_features(tx_h: pd.DataFrame, meta: pd.Series, t_idx: int) -> dict:
    """Compute the household feature vector as-of cut month index t_idx.

    Every window here is bounded by t_idx-1 — no facts from the cut month or later are
    read. Shared by the builder and the temporal-wall verifier so any leak would show up
    as a mismatch between the full-frame and hard-filtered rebuild.
    """
    prior_lo, prior_hi = t_idx - 6, t_idx - 1
    hist = tx_h[tx_h["midx"] <= t_idx - 1]
    monthly = hist.groupby("midx")["revenue_amount"].sum()
    last6 = [float(monthly.get(prior_lo + i, 0.0)) for i in range(6)]
    last12 = [float(monthly.get(t_idx - 12 + i, 0.0)) for i in range(12)]
    peak_idx = int(monthly.idxmax()) if len(monthly) else t_idx - 1
    tx_sizes_h = hist["revenue_amount"].abs()
    med_tx_12m = float(tx_sizes_h[tx_sizes_h > 0].median()) if (tx_sizes_h > 0).any() else 0.0
    tx6 = hist[hist["midx"] >= prior_lo]["revenue_amount"].abs()
    mean_tx6 = float(tx6.mean()) if len(tx6) else 0.0
    max_tx6 = float(tx6.max()) if len(tx6) else 0.0
    prods = hist[hist["product_id"].notna()]
    prod_rev = prods.groupby("product_id")["revenue_amount"].sum()
    total_pr = float(prod_rev.sum())
    hhi = float(((prod_rev / total_pr) ** 2).sum()) if total_pr > 0 else 1.0
    last_tx_idx = int(hist["midx"].max()) if len(hist) else t_idx - 12
    seg = str(meta.get("segment", "")).upper()
    risk = str(meta.get("risk_profile", "")).lower()
    return {
        "rev_trailing_3m": _window_revenue(tx_h, t_idx - 3, t_idx - 1),
        "rev_trailing_6m": _window_revenue(tx_h, prior_lo, prior_hi),
        "rev_trailing_12m": _window_revenue(tx_h, t_idx - 12, t_idx - 1),
        "rev_slope_6m": _ols_slope(last6),
        "rev_volatility_12m": float(np.std(last12)),
        "months_since_peak": max(0, (t_idx - 1) - peak_idx),
        "tx_count_3m": int(((tx_h["midx"] >= t_idx - 3) & (tx_h["midx"] <= t_idx - 1)).sum()),
        "tx_count_6m": int(((tx_h["midx"] >= prior_lo) & (tx_h["midx"] <= prior_hi)).sum()),
        "mean_tx_size_6m_ratio": (mean_tx6 / med_tx_12m) if med_tx_12m else 0.0,
        "max_tx_size_6m_ratio": (max_tx6 / med_tx_12m) if med_tx_12m else 0.0,
        "product_count": int(prod_rev.shape[0]),
        "product_diversification": 1.0 - hhi,
        "account_count": int(meta.get("account_count", 0)),
        "total_aum": float(meta.get("total_aum", 0.0)),
        "days_since_last_tx": int((t_idx - 1 - last_tx_idx) * 30),
        "seg_HNW": 1 if seg == "HNW" else 0,
        "seg_AFFLUENT": 1 if seg == "AFFLUENT" else 0,
        "risk_conservative": 1 if risk == "conservative" else 0,
        "risk_moderate": 1 if risk == "moderate" else 0,
        "risk_aggressive": 1 if risk == "aggressive" else 0,
    }


@lru_cache(maxsize=1)
def build_household_frame() -> HouseholdFrame:
    """Household × cut supervised frame with features (<= t) + both revenue-risk labels."""
    tx_rev = _load_transactions()  # product left-join keeps one row per (tx, product)
    hh = _load_households()
    rows: list[dict] = []
    hh_meta = hh.set_index("household_id")
    tx_by_hh = {hid: g for hid, g in tx_rev.groupby("household_id")}

    for cut in CUT_POINTS:
        t_idx = _month_idx(cut)
        prior_lo, prior_hi = t_idx - 6, t_idx - 1
        next_lo, next_hi = t_idx, t_idx + 5
        for hid, meta in hh_meta.iterrows():
            tx_h = tx_by_hh.get(hid)
            if tx_h is None:
                continue
            tx_h_u = tx_h.drop_duplicates(subset=["transaction_id"])  # revenue de-dup
            prior_rev = _window_revenue(tx_h_u, prior_lo, prior_hi)
            if prior_rev < ACTIVITY_FLOOR:
                continue
            next_rev = _window_revenue(tx_h_u, next_lo, next_hi)
            feats = _household_features(tx_h, meta, t_idx)
            rows.append({
                "household_id": hid, "cut": cut, **feats,
                "_next_rev_6m": next_rev,
                "label_decline": int(next_rev < DECLINE_THRESHOLD * prior_rev),
                "label_churn": int(next_rev < CHURN_THRESHOLD * prior_rev),
            })

    df = pd.DataFrame(rows)
    return HouseholdFrame(df=df, feature_cols=list(HOUSEHOLD_FEATURES))


@lru_cache(maxsize=1)
def _advisor_household_map() -> dict[str, list[str]]:
    serves = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_advisor_serves_household.csv")
    out: dict[str, list[str]] = {}
    for adv, hid in zip(serves["from_id"], serves["to_id"]):
        out.setdefault(adv, []).append(hid)
    return out


# Live forward-scoring cut: features use facts <= 2026-07 (data end), predicting the
# unobserved next 6 months. Trailing-6m window = 2026-02..2026-07.
CURRENT_CUT = "2026-08"


def build_current_household_features(advisor_id: str) -> tuple[pd.DataFrame, "pd.Series"]:
    """Per-household leakage-safe feature rows for one advisor, as-of the latest data month
    (for live forward prediction). Returns (features_df indexed by household_id, revenue
    weights). Read-only."""
    tx_rev = _load_transactions()
    hh_meta = _load_households().set_index("household_id")
    t_idx = _month_idx(CURRENT_CUT)
    prior_lo, prior_hi = t_idx - 6, t_idx - 1
    rows, weights, index = [], [], []
    for hid in _advisor_household_map().get(advisor_id, []):
        if hid not in hh_meta.index:
            continue
        tx_h = tx_rev[tx_rev["household_id"] == hid]
        tx_h_u = tx_h.drop_duplicates(subset=["transaction_id"])
        prior_rev = _window_revenue(tx_h_u, prior_lo, prior_hi)
        rows.append(_household_features(tx_h, hh_meta.loc[hid], t_idx))
        weights.append(max(prior_rev, 0.0))
        index.append(hid)
    df = pd.DataFrame(rows, index=index)[list(HOUSEHOLD_FEATURES)] if rows else pd.DataFrame(columns=HOUSEHOLD_FEATURES)
    return df, pd.Series(weights, index=index, dtype=float)


def verify_temporal_wall(sample: int = 60) -> dict:
    """Anti-leakage rule 1: recompute a sample of rows' features from a transaction frame
    HARD-FILTERED to < cut month, and assert bit-identical to the full-frame features. If
    any feature secretly read the label window, the two would diverge."""
    tx_rev = _load_transactions()
    hh_meta = _load_households().set_index("household_id")
    hf = build_household_frame()
    checked = 0
    mismatches = 0
    for _, row in hf.df.head(sample).iterrows():
        hid, cut = row["household_id"], row["cut"]
        t_idx = _month_idx(cut)
        tx_h = tx_rev[tx_rev["household_id"] == hid]
        tx_h_filtered = tx_h[tx_h["midx"] < t_idx]  # nothing from cut month onward
        feats = _household_features(tx_h_filtered, hh_meta.loc[hid], t_idx)
        for col in HOUSEHOLD_FEATURES:
            if abs(float(feats[col]) - float(row[col])) > 1e-9:
                mismatches += 1
        checked += 1
    return {"rows_checked": checked, "feature_mismatches": mismatches}


# --------------------------------------------------------------------------------------
# AGP off-track frame
# --------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _advisor_snapshot_features() -> dict[str, dict]:
    """The advisor's real Feature_Catalog behavioral features (§3.2), pulled from the
    persisted snapshot store, keeping only numeric columns that are NOT attainment-/status-
    derived (AGP_EXCLUDED). Prefixed `f_` to namespace them. Read-only; computes a snapshot
    only if one isn't already persisted."""
    from app.features.engineering import FeatureEngineeringService
    from app.features.snapshot_store import SnapshotStore

    store = SnapshotStore()
    engine = FeatureEngineeringService()
    serves = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_advisor_serves_household.csv")
    advisors = sorted(set(serves["from_id"]))
    out: dict[str, dict] = {}
    for adv in advisors:
        snap = store.latest_for_entity("ADVISOR", adv)
        vals = snap.get("features") if isinstance(snap, dict) else None
        if not vals:
            vals = engine.compute_advisor_snapshot(adv).values()
        feats = {}
        for k, v in vals.items():
            if k in AGP_EXCLUDED:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                feats[f"f_{k}"] = float(v)
        out[adv] = feats
    return out


@lru_cache(maxsize=1)
def _measurement_to_advisor() -> dict[str, str]:
    """measurement -> advisor via progress -> enrollment -> advisor (real edge traversal)."""
    prog_meas = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_progress_has_kpi_measurement.csv")
    enr_prog = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_enrollment_has_milestone_progress.csv")
    adv_enr = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_advisor_has_agp_enrollment.csv")
    prog2enr = dict(zip(enr_prog["to_id"], enr_prog["from_id"]))
    enr2adv = dict(zip(adv_enr["to_id"], adv_enr["from_id"]))
    out: dict[str, str] = {}
    for _, r in prog_meas.iterrows():
        adv = enr2adv.get(prog2enr.get(r["from_id"]))
        if adv:
            out[r["to_id"]] = adv
    return out


@lru_cache(maxsize=1)
def build_agp_frame() -> HouseholdFrame:
    """One row per KPI measurement (960) with advisor behavioral features (from raw
    transactions, NOT attainment-derived) + KPI metadata; label = status == OFF_TRACK."""
    meas = pd.read_csv(SAMPLE_DIR / "vertices" / "phx_dm_agp_kpi_measurement.csv")
    meas_kpi = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_measurement_for_kpi.csv")
    kpi_of = dict(zip(meas_kpi["from_id"], meas_kpi["to_id"]))
    m2a = _measurement_to_advisor()

    # advisor behavioral features as-of the snapshot (2026-07): raw-transaction trailing
    # revenue + the advisor's real Feature_Catalog behavioral features (§3.2), with all
    # attainment-/status-derived columns excluded (AGP_EXCLUDED) so the label never leaks.
    tx = _load_transactions().drop_duplicates(subset=["transaction_id"])
    serves = pd.read_csv(SAMPLE_DIR / "edges" / "phx_dm_advisor_serves_household.csv")
    hh2adv = dict(zip(serves["to_id"], serves["from_id"]))
    tx = tx.assign(advisor_id=tx["household_id"].map(hh2adv))
    t_idx = _month_idx("2026-07")
    snap_feats = _advisor_snapshot_features()
    adv_feats: dict[str, dict] = {}
    for adv, tx_a in tx.groupby("advisor_id"):
        if not isinstance(adv, str):
            continue
        monthly = tx_a[tx_a["midx"] <= t_idx - 1].groupby("midx")["revenue_amount"].sum()
        last6 = [float(monthly.get(t_idx - 6 + i, 0.0)) for i in range(6)]
        adv_feats[adv] = {
            "adv_rev_trailing_6m": _window_revenue(tx_a, t_idx - 6, t_idx - 1),
            "adv_rev_trailing_12m": _window_revenue(tx_a, t_idx - 12, t_idx - 1),
            "adv_rev_slope_6m": _ols_slope(last6),
            "adv_tx_count_6m": int(((tx_a["midx"] >= t_idx - 6) & (tx_a["midx"] <= t_idx - 1)).sum()),
            "adv_household_count": int(tx_a["household_id"].nunique()),
            **snap_feats.get(adv, {}),
        }

    kpi_types = sorted(set(kpi_of.values()))
    rows: list[dict] = []
    for _, r in meas.iterrows():
        mid = r["measurement_id"]
        adv = m2a.get(mid)
        if not adv or adv not in adv_feats:
            continue
        kpi = kpi_of.get(mid, "UNKNOWN")
        row = {
            "measurement_id": mid, "advisor_id": adv, "kpi_type": kpi,
            "target_value": float(pd.to_numeric(r["target_value"], errors="coerce") or 0.0),
            "label_off_track": int(str(r["status"]).upper() == "OFF_TRACK"),
            **adv_feats[adv],
        }
        for k in kpi_types:
            row[f"kpi_{k}"] = 1 if kpi == k else 0
        rows.append(row)

    df = pd.DataFrame(rows)
    feature_cols = [c for c in df.columns if c not in {
        "measurement_id", "advisor_id", "kpi_type", "label_off_track"} and c not in AGP_EXCLUDED]
    return HouseholdFrame(df=df, feature_cols=feature_cols)


# --------------------------------------------------------------------------------------
# Prevalence report (Commit 2 verification gate)
# --------------------------------------------------------------------------------------

def prevalence_report() -> dict:
    hf = build_household_frame()
    af = build_agp_frame()
    df, adf = hf.df, af.df

    # anti-leakage sanity: no feature column may equal the label window revenue
    assert "_next_rev_6m" not in hf.feature_cols
    assert not (set(hf.feature_cols) & {"label_decline", "label_churn"})

    rep = {
        "household_samples": int(len(df)),
        "households": int(df["household_id"].nunique()) if len(df) else 0,
        "cuts": CUT_POINTS,
        "decline_positive_rate": round(float(df["label_decline"].mean()), 4) if len(df) else 0.0,
        "churn_positive_rate": round(float(df["label_churn"].mean()), 4) if len(df) else 0.0,
        "churn_positives": int(df["label_churn"].sum()) if len(df) else 0,
        "agp_samples": int(len(adf)),
        "agp_off_track_rate": round(float(adf["label_off_track"].mean()), 4) if len(adf) else 0.0,
        "household_feature_count": len(hf.feature_cols),
        "agp_feature_count": len(af.feature_cols),
    }
    return rep


if __name__ == "__main__":
    import json

    print("Building household + AGP training frames from real foundation data...\n")
    rep = prevalence_report()
    print(json.dumps(rep, indent=2))
    print("\nExpected (Fable §0, measured): n≈2159 household samples, decline≈0.266, "
          "churn≈0.038 (83 pos), AGP 960 rows @ 0.64 off-track.")
    print("\nAnti-leakage temporal-wall check (rule 1):")
    wall = verify_temporal_wall()
    print(json.dumps(wall, indent=2))
    assert wall["feature_mismatches"] == 0, "TEMPORAL LEAK: features differ under hard filter"
    print("PASS — no feature reads the label window.")
