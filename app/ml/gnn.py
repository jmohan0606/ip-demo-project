from __future__ import annotations

"""GraphSAGE embeddings (Section 11.1 §7) — Tier 2 (local PyTorch-Geometric).

Tier 1 (pyTigerGraph[gds] neighborLoader) needs a live edge load, which stalls on this
2-core box (Phase 2/3 finding) — attempted-but-unverified, documented in the model card.
Tier 2 is the PRACTICAL DEFAULT: the SAME GraphSAGE architecture trained self-supervised
(link prediction) over the FoundationGraphStore's real edges, held in memory. Tier 3
(deterministic feature-projection, app/embeddings) is the final fallback.

The learned 32-dim embeddings are the GNN's OUTPUT (distinct from the interpretable feature
INPUTS). They are written to a dedicated gnn_embeddings table (managed by the VectorClient in
§8), isolated from the existing dim-8 deterministic-projection pipeline so nothing breaks.

Torch/PyG imports are local to this module (heavy-import rule).
"""

import datetime as _dt
import hashlib
import json
import math
import sqlite3
import time
from pathlib import Path

from app.config.settings import get_settings
from app.graph.foundation_store import get_foundation_store

GNN_MODEL = "graphsage-v1"
OUT_DIM = 32


def _db() -> str:
    return get_settings().sqlite_db_path


def init_gnn_table() -> None:
    Path(_db()).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_db()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS gnn_embeddings (
                entity_type TEXT, entity_id TEXT, model_name TEXT, model_version TEXT,
                dim INTEGER, vector_json TEXT, computed_at TEXT,
                PRIMARY KEY (entity_type, entity_id, model_name))"""
        )


def _build_graph():
    """Homogeneous node set (advisor/household/account) + serves/owns edges. Node-type is a
    feature, so a single SAGEConv stack learns over the whole graph — robust on 2 cores and a
    real GraphSAGE; the model card states this homogeneous-with-type-features formulation."""
    store = get_foundation_store()
    advisors = sorted(store.all_vertices("phx_dm_advisor").keys())
    households = store.all_vertices("phx_dm_household")
    accounts = store.all_vertices("phx_dm_account")
    hh_ids = sorted(households.keys())
    ac_ids = sorted(accounts.keys())

    nodes: list[tuple[str, str]] = (
        [("ADVISOR", a) for a in advisors]
        + [("HOUSEHOLD", h) for h in hh_ids]
        + [("ACCOUNT", a) for a in ac_ids]
    )
    idx = {(t, i): n for n, (t, i) in enumerate(nodes)}

    edges: list[tuple[int, int]] = []
    for e in store.edges.get("phx_dm_advisor_serves_household", []):
        u, v = ("ADVISOR", str(e["from_id"])), ("HOUSEHOLD", str(e["to_id"]))
        if u in idx and v in idx:
            edges.append((idx[u], idx[v]))
    for e in store.edges.get("phx_dm_household_owns_account", []):
        u, v = ("HOUSEHOLD", str(e["from_id"])), ("ACCOUNT", str(e["to_id"]))
        if u in idx and v in idx:
            edges.append((idx[u], idx[v]))

    # node features: [is_advisor, is_household, is_account, log1p(size)/scale, degree_norm]
    deg = [0] * len(nodes)
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    maxdeg = max(deg) or 1
    feats = []
    for n, (t, i) in enumerate(nodes):
        if t == "HOUSEHOLD":
            size = float(households[i].get("total_aum", 0) or 0)
        elif t == "ACCOUNT":
            size = float(accounts[i].get("current_value", 0) or 0)
        else:
            size = 0.0  # advisor size derived from structure/degree
        feats.append([
            1.0 if t == "ADVISOR" else 0.0,
            1.0 if t == "HOUSEHOLD" else 0.0,
            1.0 if t == "ACCOUNT" else 0.0,
            math.log1p(max(size, 0.0)) / 20.0,
            deg[n] / maxdeg,
        ])
    return nodes, feats, edges


def train_gnn() -> dict:
    import numpy as np
    import torch
    from sklearn.metrics import roc_auc_score
    from torch_geometric.nn import SAGEConv
    from torch_geometric.utils import negative_sampling

    torch.manual_seed(42)
    np.random.seed(42)
    nodes, feats, edges = _build_graph()
    x = torch.tensor(feats, dtype=torch.float32)
    ei = torch.tensor(edges, dtype=torch.long).t().contiguous()
    # undirected for message passing
    ei_undir = torch.cat([ei, ei.flip(0)], dim=1)

    # 90/10 edge split for link prediction
    m = ei.size(1)
    perm = torch.randperm(m)
    n_test = max(1, int(m * 0.1))
    test_pos = ei[:, perm[:n_test]]
    train_pos = ei[:, perm[n_test:]]
    train_msg = torch.cat([train_pos, train_pos.flip(0)], dim=1)

    class SAGE(torch.nn.Module):
        def __init__(self, in_dim, hidden, out):
            super().__init__()
            self.c1 = SAGEConv(in_dim, hidden)
            self.c2 = SAGEConv(hidden, out)

        def forward(self, x, edge_index):
            h = self.c1(x, edge_index).relu()
            return self.c2(h, edge_index)

    hidden = 64
    model = SAGE(x.size(1), hidden, OUT_DIM)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    cap_s = get_settings().ml_time_box_minutes * 60

    def score(z, edge_index):
        return (z[edge_index[0]] * z[edge_index[1]]).sum(dim=-1)

    t0 = time.time()
    epochs_run = 0
    for epoch in range(50):
        model.train()
        opt.zero_grad()
        z = model(x, train_msg)
        neg = negative_sampling(train_pos, num_nodes=x.size(0), num_neg_samples=train_pos.size(1))
        pos_s = score(z, train_pos)
        neg_s = score(z, neg)
        logits = torch.cat([pos_s, neg_s])
        labels = torch.cat([torch.ones_like(pos_s), torch.zeros_like(neg_s)])
        loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, labels)
        loss.backward()
        opt.step()
        epochs_run = epoch + 1
        if (time.time() - t0) > cap_s:
            break

    model.eval()
    with torch.no_grad():
        z = model(x, ei_undir)
        neg_test = negative_sampling(ei, num_nodes=x.size(0), num_neg_samples=test_pos.size(1))
        y = torch.cat([torch.ones(test_pos.size(1)), torch.zeros(neg_test.size(1))]).numpy()
        s = torch.cat([score(z, test_pos), score(z, neg_test)]).sigmoid().numpy()
        auc = float(roc_auc_score(y, s))
        emb = z.numpy()

    # persist embeddings to the dedicated gnn table
    init_gnn_table()
    now = _dt.datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(_db()) as conn:
        conn.execute("DELETE FROM gnn_embeddings WHERE model_name=?", (GNN_MODEL,))
        for n, (t, i) in enumerate(nodes):
            conn.execute("REPLACE INTO gnn_embeddings VALUES (?,?,?,?,?,?,?)",
                         (t, i, GNN_MODEL, "1.0", OUT_DIM,
                          json.dumps([round(float(v), 5) for v in emb[n]]), now))

    counts: dict[str, int] = {}
    for t, _ in nodes:
        counts[t] = counts.get(t, 0) + 1

    print("=" * 72)
    print("GraphSAGE (Tier 2, local PyG) — self-supervised link prediction")
    print("=" * 72)
    print(f"  nodes={len(nodes)} ({counts}) edges={ei.size(1)} epochs={epochs_run} wall={time.time()-t0:.1f}s")
    print(f"  held-out link-prediction ROC-AUC = {auc:.4f}")

    from app.ml import registry
    art_note = registry.artifact_dir() / f"{GNN_MODEL}.json"  # metadata marker (embeddings in SQLite)
    art_note.write_text(json.dumps({"model": GNN_MODEL, "auc": auc, "dim": OUT_DIM}))
    sha = hashlib.sha256(art_note.read_bytes()).hexdigest()[:16]
    entry = {
        "name": GNN_MODEL, "version": "1.0",
        "algorithm": "GraphSAGE (2-layer SAGEConv, hidden 64→out 32) · Tier 2 local PyTorch-Geometric · "
                     "homogeneous with node-type features · self-supervised link prediction",
        "training_date": now,
        "training_data": f"real FoundationGraphStore: {len(nodes)} nodes "
                         f"({counts}), {ei.size(1)} serves/owns edges",
        "label_definition": "self-supervised link prediction (serves + owns edges, 10% held out) with negative sampling",
        "split": "90/10 edge split", "metrics": {"link_pred_roc_auc": round(auc, 4), "epochs": epochs_run},
        "primary_metric": "link_pred_roc_auc", "primary_metric_value": round(auc, 4),
        "quality_floor": 0.6,
        "features": ["node-type one-hot", "log1p(size)", "degree"],
        "caveats": "Tier 2 (local PyG) actually ran; Tier 1 (pyTigerGraph[gds] neighborLoader) not "
                   "verified on this 2-core box (live edge load stalls). 32-dim output embeddings.",
        "artifact_path": str(art_note), "artifact_sha256": sha,
        "served_by": f"{GNN_MODEL} (tier2-local-pyg)",
        "quality_gate": "passed" if auc >= 0.6 else "failed",
        "served_since": now if auc >= 0.6 else None,
        "gnn_tier_ran": "tier2-local-pyg",
    }
    registry.upsert_entry(entry)
    return {"nodes": len(nodes), "edges": int(ei.size(1)), "roc_auc": round(auc, 4),
            "counts": counts, "gate": entry["quality_gate"]}


if __name__ == "__main__":
    train_gnn()
