from __future__ import annotations

"""Section 11.3 Part B — outcome-labeled pair construction from the real feedback chain.

Reads the GRAPH STORE (so it sees seeded rows AND any runtime-submitted feedback — real
recorded history, not a parallel table). Walks each learning signal through
LS→recommendation and LS→outcome→feedback, resolves the advisor/household entity, labels the
event positive/negative, and builds contrastive pairs (pull successful situations together,
push failed ones apart). Deterministic, capped, with a seeded 20% holdout for honest metrics.

No heavy ML imports here — this only shapes id pairs; the fine-tune (fl_finetune.py) maps
them to GNN node indices.
"""

import json
import random
import zlib

from app.graph.foundation_store import get_foundation_store

# Read-time legacy-vocab map (seed rows use DEFER/NOT_RELEVANT, absent from live ACTION_SIGNALS).
_VOCAB = {"DEFER": "IGNORE", "NOT_RELEVANT": "REJECT"}
_POSITIVE_ACTIONS = {"ACCEPT", "COMPLETE", "MODIFY"}
_PAIR_CAP = 600  # per (family, pair-type)
_HOLDOUT = 0.20


def _rng(*key) -> random.Random:
    return random.Random(zlib.crc32(":".join(str(k) for k in key).encode()))


def _title_family(store, rec_id: str) -> str | None:
    rec = store.vertex("phx_dm_recommendation", rec_id)
    if not rec:
        return None
    a = str(rec.get("action_text", "")).lower()
    if "concentration" in a or "product" in a:
        return "MANAGED_MIX"
    if "relationship" in a or "growth" in a:
        return "RETENTION"
    if "crm" in a or "follow" in a or "pipeline" in a:
        return "CRM_EXECUTION"
    return None


def _resolve_entity(store, rec_id: str) -> tuple[str | None, str | None]:
    """Return (advisor_id, household_id|None) for a recommendation's target."""
    adv = store.out_ids("phx_dm_recommendation_for_advisor", rec_id)
    if adv:
        return adv[0], None
    hh = store.out_ids("phx_dm_recommendation_for_household", rec_id)
    if hh:
        serving = store.in_ids("phx_dm_advisor_serves_household", hh[0])
        return (serving[0] if serving else None), hh[0]
    ac = store.out_ids("phx_dm_recommendation_for_account", rec_id)
    if ac:
        owner = store.in_ids("phx_dm_household_owns_account", ac[0])
        hh_id = owner[0] if owner else None
        serving = store.in_ids("phx_dm_advisor_serves_household", hh_id) if hh_id else []
        return (serving[0] if serving else None), hh_id
    return None, None


def build_events(store=None) -> list[dict]:
    """Labeled events from the real chain: (family, advisor, household|None, polarity, ts)."""
    store = store or get_foundation_store()
    events = []
    for lid, ls in store.all_vertices("phx_dm_learning_signal").items():
        try:
            sj = json.loads(ls.get("signal_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            sj = {}
        rec_ids = store.out_ids("phx_dm_learning_updates_recommendation", lid)
        if not rec_ids:
            continue
        rec_id = rec_ids[0]
        family = sj.get("family") or _title_family(store, rec_id)
        if not family:
            continue
        action = _VOCAB.get(str(sj.get("action", "")).upper(), str(sj.get("action", "")).upper())
        # outcome_value: from signal_json, else walk LS→OUT
        outcome_value = sj.get("outcome_value")
        if outcome_value is None:
            outs = store.out_ids("phx_dm_learning_from_outcome", lid)
            if outs:
                ov = store.vertex("phx_dm_outcome_event", outs[0])
                outcome_value = float(ov.get("outcome_value", 0)) if ov else 0.0
            else:
                outcome_value = 0.0
        label = sj.get("label")
        if label not in ("positive", "negative"):
            label = "positive" if (action in _POSITIVE_ACTIONS and float(outcome_value) >= 0) else "negative"
        adv, hh = _resolve_entity(store, rec_id)
        if not adv:
            continue
        events.append({
            "ls_id": lid, "family": family, "advisor": adv, "household": hh,
            "polarity": label, "action": action, "outcome_value": float(outcome_value),
            "created_at": str(ls.get("created_at", "")),
        })
    events.sort(key=lambda e: (e["created_at"], e["ls_id"]))
    return events


def build_pairs(store=None) -> dict:
    """Contrastive pairs from the labeled events. Returns train/holdout pair lists +
    per-family positive/negative advisor sets (for the affinity centroids, §4.5)."""
    events = build_events(store)
    by_fam: dict[str, dict[str, set]] = {}
    rel_pos, rel_neg = [], []  # (advisor, household) relationship pairs
    for e in events:
        fam = e["family"]
        by_fam.setdefault(fam, {"positive": set(), "negative": set()})
        by_fam[fam][e["polarity"]].add(e["advisor"])
        if e["household"]:
            (rel_pos if e["polarity"] == "positive" else rel_neg).append((e["advisor"], e["household"]))

    pairs: list[tuple] = []  # (("ADVISOR",a),("ADVISOR",b), sign, family, ptype)
    for fam, sets in by_fam.items():
        pos = sorted(sets["positive"])
        neg = sorted(sets["negative"])
        # P1: same-family positive advisor pairs -> pull (+1)
        p1 = [(("ADVISOR", pos[i]), ("ADVISOR", pos[j])) for i in range(len(pos)) for j in range(i + 1, len(pos))]
        # P2: positive vs negative in the same family -> push (-1)
        p2 = [(("ADVISOR", a), ("ADVISOR", b)) for a in pos for b in neg if a != b]
        for lst, sign, ptype in [(p1, 1, "P1"), (p2, -1, "P2")]:
            if len(lst) > _PAIR_CAP:
                lst = _rng("cap", fam, ptype).sample(lst, _PAIR_CAP)
            pairs += [(u, v, sign, fam, ptype) for (u, v) in lst]
    # P3/P4 relationship pairs (uncapped, small)
    for (a, h) in rel_pos:
        pairs.append((("ADVISOR", a), ("HOUSEHOLD", h), 1, None, "P3"))
    for (a, h) in rel_neg:
        pairs.append((("ADVISOR", a), ("HOUSEHOLD", h), -1, None, "P4"))

    # seeded 20% holdout, stratified by (ptype, family)
    train, holdout = [], []
    strata: dict[tuple, list] = {}
    for p in pairs:
        strata.setdefault((p[4], p[3]), []).append(p)
    for key, lst in strata.items():
        r = _rng("holdout", *[str(k) for k in key])
        idx = list(range(len(lst)))
        r.shuffle(idx)
        cut = int(len(lst) * _HOLDOUT)
        hold = set(idx[:cut])
        for i, p in enumerate(lst):
            (holdout if i in hold else train).append(p)

    stats = {"events": len(events), "pairs_total": len(pairs), "train": len(train), "holdout": len(holdout),
             "by_type_family": {f"{p[4]}/{p[3]}": 0 for p in pairs}}
    for p in pairs:
        stats["by_type_family"][f"{p[4]}/{p[3]}"] += 1
    fam_sets = {f: {"positive": sorted(s["positive"]), "negative": sorted(s["negative"])}
                for f, s in by_fam.items()}
    return {"events": events, "train": train, "holdout": holdout, "stats": stats, "family_sets": fam_sets}


if __name__ == "__main__":
    r = build_pairs()
    print(json.dumps(r["stats"], indent=2))
    print("family sets:", {f: {k: len(v) for k, v in s.items()} for f, s in r["family_sets"].items()})
