"""Next-best-product propensity — a household-level extension of the Section 11.1 model tier.

Reuses the existing model-tier plumbing (registry entry + ModelClient method + a
`/predictions/*` endpoint, mirroring `household_churn`) rather than building a parallel
stack. It is a *collaborative-propensity* scorer, not a supervised classifier: the demo
data has static holdings (no timestamped adoption events), so a supervised "will adopt
category X next" label would be fabricated. Instead we compute a real, explainable signal
directly from the holdings graph:

  For a household H in segment S, and each product category C that H does NOT yet hold:
     propensity(C) = 0.70 * peer_adoption(C, S) + 0.30 * overall_adoption(C)
  where peer_adoption(C, S) = fraction of segment-S households holding C, and
  overall_adoption(C) = fraction of ALL households holding C.

Every number traces to real edges (advisor→household→account→product→subcategory→category).
The response carries the method + a caveat so the UI can badge it honestly, exactly like the
household-churn surface. Deterministic and available in both MODEL_CLIENT_MODE tiers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.config.settings import get_settings

MODEL_NAME = "next-best-product-cf"


def _sample_dir() -> Path:
    return Path(get_settings().foundation_dir) / "data" / "sample"


@lru_cache(maxsize=1)
def _holdings() -> tuple[pd.DataFrame, dict[str, str], dict[str, str]]:
    """Return (household_category_holdings, household->segment, category_id->name).

    household_category_holdings: DataFrame[household_id, category_id] (one row per held pair).
    """
    d = _sample_dir()
    v, e = d / "vertices", d / "edges"

    households = pd.read_csv(v / "phx_dm_household.csv", dtype=str)
    hh_segment = dict(zip(households["household_id"], households["segment"]))

    categories = pd.read_csv(v / "phx_dm_product_category.csv", dtype=str)
    cat_name = dict(zip(categories["category_id"], categories["category_name"]))

    owns = pd.read_csv(e / "phx_dm_household_owns_account.csv", dtype=str)  # hh -> account
    holds = pd.read_csv(e / "phx_dm_account_holds_product.csv", dtype=str)  # account -> product
    prod_sub = pd.read_csv(e / "phx_dm_product_in_subcategory.csv", dtype=str)  # product -> subcat
    sub_cat = pd.read_csv(e / "phx_dm_subcategory_in_category.csv", dtype=str)  # subcat -> category

    # household → account → product → subcategory → category
    chain = (
        owns.rename(columns={"from_id": "household_id", "to_id": "account_id"})
        .merge(holds.rename(columns={"from_id": "account_id", "to_id": "product_id"}), on="account_id")
        .merge(prod_sub.rename(columns={"from_id": "product_id", "to_id": "subcategory_id"}), on="product_id")
        .merge(sub_cat.rename(columns={"from_id": "subcategory_id", "to_id": "category_id"}), on="subcategory_id")
    )
    hc = chain[["household_id", "category_id"]].drop_duplicates().reset_index(drop=True)
    return hc, hh_segment, cat_name


@lru_cache(maxsize=1)
def _adoption_tables() -> tuple[dict[str, float], dict[tuple[str, str], float], dict[str, set[str]]]:
    """Precompute overall + per-segment category adoption rates and each household's held set."""
    hc, hh_segment, _ = _holdings()
    all_hh = set(hh_segment)
    total = len(all_hh) or 1

    overall: dict[str, float] = {}
    for cat, grp in hc.groupby("category_id"):
        overall[cat] = len(set(grp["household_id"])) / total

    # segment sizes
    seg_hh: dict[str, set[str]] = {}
    for hid, seg in hh_segment.items():
        seg_hh.setdefault(seg, set()).add(hid)

    peer: dict[tuple[str, str], float] = {}
    hc = hc.assign(segment=hc["household_id"].map(hh_segment))
    for (cat, seg), grp in hc.groupby(["category_id", "segment"]):
        denom = len(seg_hh.get(seg, set())) or 1
        peer[(cat, seg)] = len(set(grp["household_id"])) / denom

    held_by_hh: dict[str, set[str]] = {}
    for hid, cat in zip(hc["household_id"], hc["category_id"]):
        held_by_hh.setdefault(hid, set()).add(cat)
    return overall, peer, held_by_hh


def _advisor_households(advisor_id: str) -> list[str]:
    e = _sample_dir() / "edges"
    serves = pd.read_csv(e / "phx_dm_advisor_serves_household.csv", dtype=str)
    return serves.loc[serves["from_id"] == advisor_id, "to_id"].drop_duplicates().tolist()


def next_best_product(advisor_id: str, top_n: int = 3) -> dict:
    """Per-household ranked next-best product categories for an advisor's book."""
    _, hh_segment, cat_name = _holdings()
    overall, peer, held_by_hh = _adoption_tables()
    all_categories = set(cat_name)

    hh_ids = _advisor_households(advisor_id)
    households = []
    for hid in hh_ids:
        seg = hh_segment.get(hid, "")
        held = held_by_hh.get(hid, set())
        gaps = all_categories - held
        scored = []
        for cat in gaps:
            peer_rate = peer.get((cat, seg), 0.0)
            all_rate = overall.get(cat, 0.0)
            propensity = 0.70 * peer_rate + 0.30 * all_rate
            if propensity <= 0:
                continue
            scored.append({
                "category_id": cat,
                "category_name": cat_name.get(cat, cat),
                "propensity": round(float(propensity), 4),
                "peer_adoption": round(float(peer_rate), 4),
                "overall_adoption": round(float(all_rate), 4),
                "reason": (
                    f"{round(peer_rate * 100)}% of {seg or 'peer'} households hold "
                    f"{cat_name.get(cat, cat)}; this household does not."
                ),
            })
        scored.sort(key=lambda r: r["propensity"], reverse=True)
        households.append({
            "household_id": hid,
            "segment": seg,
            "held_categories": sorted(cat_name.get(c, c) for c in held),
            "next_best": scored[:top_n],
        })

    # Rank households by their single best opportunity so the UI can lead with the strongest.
    households.sort(key=lambda h: (h["next_best"][0]["propensity"] if h["next_best"] else 0.0), reverse=True)
    return {
        "available": bool(hh_ids),
        "advisor_id": advisor_id,
        "model": MODEL_NAME,
        "method": "collaborative-propensity",
        "served": True,
        "caveat": (
            "Collaborative propensity from real holdings graph (segment peer-adoption blended "
            "with overall penetration). Not a supervised adoption-forecast — the demo data has "
            "static holdings with no timestamped adoption events; directional next-best signal."
        ),
        "households": households,
    }
