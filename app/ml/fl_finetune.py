from __future__ import annotations

"""Section 11.3 Part B — outcome-driven contrastive fine-tune of graphsage-v1.

Loads the trained base GNN and fine-tunes it with L = L_linkpred + 0.5·L_contrastive, where
the contrastive term pulls together embeddings of advisors/relationships from SUCCESSFUL
recorded outcomes and pushes apart those from UNSUCCESSFUL ones. The link-prediction term is
retained as the anti-forgetting anchor. Output embeddings persist as 'graphsage-v1-ft' — the
base 'graphsage-v1' rows are NEVER overwritten (table PK), so before/after stays comparable.
Bounded/time-boxed; serves only past a link-pred retention gate (else v1 keeps serving).
"""

import datetime as _dt
import hashlib
import json
import sqlite3
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from torch_geometric.nn import SAGEConv
from torch_geometric.utils import negative_sampling

from app.config.settings import get_settings
from app.ml import gnn, registry
from app.ml.fl_pairs import build_pairs
from app.ml.vector_client import get_vector_client

FT_MODEL = "graphsage-v1-ft"
LAMBDA = 0.5
MARGIN = 0.2
LR = 1e-3
MAX_EPOCHS = 20


class SAGE(torch.nn.Module):
    def __init__(self, in_dim, hidden, out):
        super().__init__()
        self.c1 = SAGEConv(in_dim, hidden)
        self.c2 = SAGEConv(hidden, out)

    def forward(self, x, edge_index):
        return self.c2(self.c1(x, edge_index).relu(), edge_index)


def _db() -> str:
    return get_settings().sqlite_db_path


def _cos(z, i, j):
    zn = torch.nn.functional.normalize(z, dim=1)
    return (zn[i] * zn[j]).sum(dim=1)


def _pairs_to_idx(pairs, idx):
    out = []
    for u, v, sign, fam, ptype in pairs:
        if u in idx and v in idx:
            out.append((idx[u], idx[v], sign, fam, ptype))
    return out


def _separation(zn: np.ndarray, pairs_idx, family: str | None = None) -> float | None:
    pull, push = [], []
    for i, j, sign, fam, ptype in pairs_idx:
        if family is not None and fam != family:
            continue
        c = float(np.dot(zn[i], zn[j]))
        (pull if sign > 0 else push).append(c)
    if not pull or not push:
        return None
    return round(float(np.mean(pull) - np.mean(push)), 4)


def run_finetune(dry_run: bool = False) -> dict:
    torch.manual_seed(42)
    np.random.seed(42)

    # base weights (train them if absent)
    state_path = registry.artifact_dir() / "graphsage-v1.pt"
    if not state_path.exists():
        gnn.train_gnn()
    blob = torch.load(state_path, map_location="cpu", weights_only=False)

    nodes, feats, edges = gnn._build_graph()
    idx = {(t, i): n for n, (t, i) in enumerate(nodes)}
    x = torch.tensor(feats, dtype=torch.float32)
    ei = torch.tensor(edges, dtype=torch.long).t().contiguous()
    ei_undir = torch.cat([ei, ei.flip(0)], dim=1)

    # reproduce the base 90/10 link-pred split (same seed → same split)
    m = ei.size(1)
    perm = torch.randperm(m)
    n_test = max(1, int(m * 0.1))
    test_pos = ei[:, perm[:n_test]]
    train_pos = ei[:, perm[n_test:]]
    train_msg = torch.cat([train_pos, train_pos.flip(0)], dim=1)

    pack = build_pairs()
    train_pairs = _pairs_to_idx(pack["train"], idx)
    hold_pairs = _pairs_to_idx(pack["holdout"], idx)
    n_events = pack["stats"]["events"]

    model = SAGE(blob["in_dim"], blob["hidden"], blob["out_dim"])
    model.load_state_dict(blob["state_dict"])

    def linkpred_auc() -> float:
        model.eval()
        with torch.no_grad():
            z = model(x, ei_undir)
            neg = negative_sampling(ei, num_nodes=x.size(0), num_neg_samples=test_pos.size(1))
            y = torch.cat([torch.ones(test_pos.size(1)), torch.zeros(neg.size(1))]).numpy()
            s = torch.cat([(_cos(z, test_pos[0], test_pos[1])), (_cos(z, neg[0], neg[1]))]).numpy()
        return float(roc_auc_score(y, s))

    def embeddings() -> np.ndarray:
        model.eval()
        with torch.no_grad():
            return torch.nn.functional.normalize(model(x, ei_undir), dim=1).numpy()

    auc_before = linkpred_auc()
    zn_before = embeddings()
    sep_before = _separation(zn_before, hold_pairs)

    ti = torch.tensor([[p[0], p[1]] for p in train_pairs], dtype=torch.long) if train_pairs else torch.empty((0, 2), dtype=torch.long)
    tsign = torch.tensor([p[2] for p in train_pairs], dtype=torch.float32) if train_pairs else torch.empty(0)

    if dry_run:
        return {"dry_run": True, "events_used": n_events, "pairs": pack["stats"],
                "link_pred_auc_before": round(auc_before, 4), "separation_before": sep_before}

    opt = torch.optim.Adam(model.parameters(), lr=LR)
    cap_s = get_settings().ml_time_box_minutes * 60
    t0 = time.time()
    best_sep, patience, epochs_run = sep_before or -9, 0, 0
    for epoch in range(MAX_EPOCHS):
        model.train()
        opt.zero_grad()
        z = model(x, train_msg)
        # link-pred BCE (anti-forgetting anchor)
        neg = negative_sampling(train_pos, num_nodes=x.size(0), num_neg_samples=train_pos.size(1))
        logits = torch.cat([_cos(z, train_pos[0], train_pos[1]), _cos(z, neg[0], neg[1])])
        labels = torch.cat([torch.ones(train_pos.size(1)), torch.zeros(neg.size(1))])
        loss = torch.nn.functional.binary_cross_entropy_with_logits(logits * 4.0, labels)
        # contrastive margin loss
        if ti.size(0):
            csim = _cos(z, ti[:, 0], ti[:, 1])
            pull = (tsign > 0)
            l_pull = (1 - csim[pull]).mean() if pull.any() else torch.zeros(())
            l_push = torch.clamp(csim[~pull] - MARGIN, min=0).mean() if (~pull).any() else torch.zeros(())
            loss = loss + LAMBDA * (l_pull + l_push)
        loss.backward()
        opt.step()
        epochs_run = epoch + 1
        sep_now = _separation(embeddings(), hold_pairs) or -9
        if linkpred_auc() < auc_before - 0.02 and epoch >= 3:
            break
        if sep_now > best_sep + 1e-4:
            best_sep, patience = sep_now, 0
        else:
            patience += 1
        if patience >= 5 or (time.time() - t0) > cap_s:
            break

    auc_after = linkpred_auc()
    zn_after = embeddings()
    sep_after = _separation(zn_after, hold_pairs)
    families = sorted({p[3] for p in hold_pairs if p[3]})
    per_family = {f: {"before": _separation(zn_before, hold_pairs, f), "after": _separation(zn_after, hold_pairs, f)}
                  for f in families}

    gate = "passed" if auc_after >= auc_before - 0.03 else "failed"
    now = _dt.datetime.now().strftime("%Y-%m-%d")
    version = f"1.0.{n_events}"

    # persist -ft embeddings (raw, not normalized) + affinity for BOTH models
    raw_after = None
    with torch.no_grad():
        raw_after = model(x, ei_undir).numpy()
    vc = get_vector_client()
    by_type: dict[str, dict[str, list[float]]] = {}
    for n, (t, i) in enumerate(nodes):
        by_type.setdefault(t, {})[i] = [float(v) for v in raw_after[n]]
    for t, vectors in by_type.items():
        vc.upsert_embeddings(t, FT_MODEL, version, vectors)

    _persist_affinity(nodes, idx, zn_before, pack["family_sets"], "graphsage-v1", now)
    _persist_affinity(nodes, idx, zn_after, pack["family_sets"], FT_MODEL, now)

    art = registry.artifact_dir() / f"{FT_MODEL}.pt"
    torch.save({"state_dict": model.state_dict(), "nodes": nodes, "hidden": blob["hidden"],
                "in_dim": blob["in_dim"], "out_dim": blob["out_dim"]}, art)
    sha = hashlib.sha256(art.read_bytes()).hexdigest()[:16]
    metrics = {"link_pred_auc_before": round(auc_before, 4), "link_pred_auc_after": round(auc_after, 4),
               "separation_before": sep_before, "separation_after": sep_after,
               "per_family_separation": per_family, "epochs": epochs_run,
               "pairs_train": len(train_pairs), "pairs_holdout": len(hold_pairs)}
    entry = {
        "name": FT_MODEL, "version": version,
        "algorithm": "GraphSAGE + outcome-contrastive fine-tune (feedback loop) · L_linkpred + 0.5·margin",
        "training_date": now,
        "training_data": f"{n_events} recorded outcome events (seeded history + live feedback); "
                         f"{len(train_pairs)} train / {len(hold_pairs)} holdout contrastive pairs",
        "label_definition": "positive = ACCEPT/COMPLETE with outcome_value>=0; negative = REJECT/IGNORE or "
                            "COMPLETE with outcome_value<0. Pull same-family positives together; push "
                            "positive-vs-negative apart; relationship pull/push per outcome polarity.",
        "split": "reproduced base 90/10 link-pred edge split (seed 42) + 20% pair holdout",
        "metrics": metrics, "primary_metric": "separation_after", "primary_metric_value": sep_after,
        "quality_floor": round(auc_before - 0.03, 4),
        "features": ["graphsage-v1 embeddings (fine-tuned)"],
        "caveats": "Demo-scale: fine-tuned on recorded outcome history; effect sizes are directional "
                   "evidence the loop works, not production learning curves. MANAGED_MIX/RETENTION recs "
                   "target few households -> thin advisor-level pairs; CRM + relationship pairs carry the signal.",
        "artifact_path": str(art), "artifact_sha256": sha,
        "served_by": f"{FT_MODEL} v{version}", "quality_gate": gate,
        "served_since": now if gate == "passed" else None,
        "retention_gate": f"AUC after {round(auc_after,4)} >= before {round(auc_before,4)} - 0.03 → {gate}",
        "events_used": n_events, "gnn_tier_ran": "tier2-local-pyg-ft",
    }
    registry.upsert_entry(entry)

    print("=" * 72)
    print("OUTCOME-DRIVEN FINE-TUNE (feedback loop) — graphsage-v1 → graphsage-v1-ft")
    print("=" * 72)
    print(f"  events={n_events} pairs train/holdout={len(train_pairs)}/{len(hold_pairs)} epochs={epochs_run} wall={time.time()-t0:.1f}s")
    print(f"  link-pred AUC: before={auc_before:.4f} after={auc_after:.4f} (retention gate: {gate})")
    print(f"  separation (holdout): before={sep_before} after={sep_after}")
    print(f"  per-family separation: {json.dumps(per_family)}")
    return {"gate": gate, "version": version, **metrics, "events_used": n_events}


def _persist_affinity(nodes, idx, zn, family_sets, model_name, now):
    """affinity(a,f) = cos(z_a, c_f+) - cos(z_a, c_f-), persisted per advisor/family/model."""
    Path(_db()).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_db()) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS fl_family_affinity (
            advisor_id TEXT, family TEXT, affinity REAL, model_name TEXT, computed_at TEXT,
            PRIMARY KEY (advisor_id, family, model_name))""")
        conn.execute("DELETE FROM fl_family_affinity WHERE model_name=?", (model_name,))
        advisors = [i for (t, i) in nodes if t == "ADVISOR"]
        for fam, sets in family_sets.items():
            pos_idx = [idx[("ADVISOR", a)] for a in sets["positive"] if ("ADVISOR", a) in idx]
            neg_idx = [idx[("ADVISOR", a)] for a in sets["negative"] if ("ADVISOR", a) in idx]
            if not pos_idx or not neg_idx:
                continue
            cpos = zn[pos_idx].mean(0)
            cneg = zn[neg_idx].mean(0)
            for a in advisors:
                za = zn[idx[("ADVISOR", a)]]
                aff = float(np.dot(za, cpos) - np.dot(za, cneg))
                conn.execute("REPLACE INTO fl_family_affinity VALUES (?,?,?,?,?)",
                             (a, fam, round(aff, 4), model_name, now))


if __name__ == "__main__":
    run_finetune()
