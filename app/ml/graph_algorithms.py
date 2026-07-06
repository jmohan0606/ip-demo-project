from __future__ import annotations

"""Classical graph algorithms (Section 11.1 §6) — deterministic-first via networkx.

Nothing here requires a live TigerGraph query INSTALL (the 2-core hardware limit). The
deterministic-mode implementation runs networkx over the FoundationGraphStore's in-memory
graph; the TigerGraph-native GDS path (Featurizer.installAlgorithm) is documented as a
fallback for a bigger box, same honest pattern as every other adapter.

Each algorithm serves ONE named screen (no algorithm without a purpose):
  - PageRank → "Referral Network Position" (CRM Activities / Advisor 360)
  - Louvain  → "Peer Communities" (AGP page)
Similarity (existing app/embeddings) is upgraded to GNN vectors in §7, untouched here.
"""

import json
import sqlite3
from pathlib import Path

from app.config.settings import get_settings
from app.graph.foundation_store import get_foundation_store

# Edges that make up the referral / book network. Products + opportunities act as shared
# hubs so the advisor graph is connected (advisors selling into the same products link up),
# which is what makes PageRank meaningfully differentiate connectors.
_REFERRAL_EDGES = [
    "phx_dm_advisor_serves_household",
    "phx_dm_advisor_has_crm_referral",
    "phx_dm_referral_for_household",
    "phx_dm_referral_generates_crm_opportunity",
    "phx_dm_advisor_has_crm_opportunity",
    "phx_dm_crm_opportunity_for_product",
]


def _db() -> str:
    return get_settings().sqlite_db_path


def _init_table() -> None:
    Path(_db()).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_db()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS graph_metrics (
                entity_type TEXT, entity_id TEXT, metric TEXT, value REAL,
                detail_json TEXT, run_id TEXT, computed_at TEXT,
                PRIMARY KEY (entity_type, entity_id, metric))"""
        )


def _build_graph():
    import networkx as nx

    store = get_foundation_store()
    g = nx.Graph()
    for edge in _REFERRAL_EDGES:
        for e in store.edges.get(edge, []):
            a, b = str(e.get("from_id")), str(e.get("to_id"))
            if a and b:
                g.add_edge(a, b)
    return g, store


def _advisor_ids(store) -> list[str]:
    return sorted(store.all_vertices("phx_dm_advisor").keys())


def _all_advisor_embeddings() -> tuple[dict[str, list[float]], str]:
    """ADVISOR embedding vectors for the Louvain kNN graph. Prefers the GNN embeddings
    (gnn_embeddings table, §7) when present — so Peer Communities upgrade to GraphSAGE
    vectors automatically — else falls back to the deterministic-projection table."""
    path = _db()
    if not Path(path).exists():
        return {}, "none"
    out: dict[str, list[float]] = {}
    from app.ml import registry as _reg

    active = _reg.active_embedding_model()  # graphsage-v1-ft when outcome-fine-tuned (§11.3)
    with sqlite3.connect(path) as conn:
        try:
            rows = conn.execute(
                "SELECT entity_id, vector_json FROM gnn_embeddings WHERE entity_type='ADVISOR' "
                "AND model_name=?", (active,)).fetchall()
            source = active
        except sqlite3.OperationalError:
            rows = []
            source = "none"
        if not rows:
            try:
                rows = conn.execute(
                    "SELECT entity_id, vector_json FROM embeddings WHERE entity_type='ADVISOR' "
                    "ORDER BY generated_at").fetchall()
                source = "deterministic-projection"
            except sqlite3.OperationalError:
                return {}, "none"
    for eid, vj in rows:
        try:
            out[eid] = [float(x) for x in json.loads(vj)]
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return out, source


def compute() -> dict:
    """Run PageRank + Louvain and persist to graph_metrics. Returns a summary. Seconds on
    this graph size; call on demand, never on boot."""
    import networkx as nx
    import numpy as np

    _init_table()
    g, store = _build_graph()
    advisors = _advisor_ids(store)
    run_id = f"gm_{store.load_report.get('total_rows', 0)}"

    pr = nx.pagerank(g, alpha=0.85) if g.number_of_nodes() else {}
    adv_pr = {a: float(pr.get(a, 0.0)) for a in advisors}
    ranked = sorted(adv_pr.values())
    n = len(ranked) or 1

    def pctile(v: float) -> float:
        return round(100.0 * sum(1 for x in ranked if x <= v) / n, 1)

    # Louvain over advisor kNN graph (k=5, cosine over embeddings)
    emb, emb_source = _all_advisor_embeddings()
    communities: dict[str, int] = {}
    community_members: dict[int, list[str]] = {}
    if len(emb) >= 5:
        ids = [a for a in advisors if a in emb]
        M = np.asarray([emb[a] for a in ids], dtype=float)
        norm = np.linalg.norm(M, axis=1, keepdims=True)
        norm[norm == 0] = 1.0
        Mn = M / norm
        sim = Mn @ Mn.T
        knn = nx.Graph()
        knn.add_nodes_from(ids)
        for i, a in enumerate(ids):
            order = np.argsort(-sim[i])
            added = 0
            for j in order:
                if j == i:
                    continue
                knn.add_edge(a, ids[j], weight=float(sim[i, j]))
                added += 1
                if added >= 5:
                    break
        parts = nx.algorithms.community.louvain_communities(knn, seed=42, weight="weight")
        for cid, members in enumerate(parts):
            for a in members:
                communities[a] = cid
            community_members[cid] = sorted(members)

    now = get_settings().app_version  # avoid Date.now(); a stable stamp is fine here
    with sqlite3.connect(_db()) as conn:
        for a in advisors:
            conn.execute(
                "REPLACE INTO graph_metrics VALUES (?,?,?,?,?,?,?)",
                ("ADVISOR", a, "referral_pagerank", adv_pr[a],
                 json.dumps({"percentile": pctile(adv_pr[a]), "degree": g.degree(a) if a in g else 0}),
                 run_id, now))
            if a in communities:
                conn.execute(
                    "REPLACE INTO graph_metrics VALUES (?,?,?,?,?,?,?)",
                    ("ADVISOR", a, "peer_community", float(communities[a]),
                     json.dumps({"community_id": communities[a]}), run_id, now))

    return {
        "advisors": len(advisors),
        "graph_nodes": g.number_of_nodes(),
        "graph_edges": g.number_of_edges(),
        "communities": len(community_members),
        "community_embedding_source": emb_source,
        "community_sizes": {str(c): len(m) for c, m in community_members.items()},
        "top_referral_hubs": sorted(
            [{"advisor_id": a, "pagerank": round(adv_pr[a], 5), "percentile": pctile(adv_pr[a])}
             for a in advisors], key=lambda r: -r["pagerank"])[:5],
    }


def referral_position(advisor_id: str) -> dict:
    """Referral Network Position for one advisor (percentile within the firm)."""
    _init_table()
    with sqlite3.connect(_db()) as conn:
        row = conn.execute(
            "SELECT value, detail_json FROM graph_metrics WHERE entity_type='ADVISOR' "
            "AND entity_id=? AND metric='referral_pagerank'", (advisor_id,)).fetchone()
    if not row:
        return {"available": False, "advisor_id": advisor_id}
    detail = json.loads(row[1] or "{}")
    pct = detail.get("percentile", 0)
    tier = "strong referral hub" if pct >= 75 else ("connected" if pct >= 40 else "peripheral")
    return {
        "available": True, "advisor_id": advisor_id, "pagerank": round(float(row[0]), 5),
        "percentile": pct, "degree": detail.get("degree", 0), "tier": tier,
        "summary": f"Referral network position: {tier} — connected to {detail.get('degree', 0)} "
                   f"entities in the referral/book network (top {round(100 - pct, 1)}% of the firm).",
    }


def peer_communities() -> dict:
    """All detected peer communities with membership + distinguishing features."""
    from app.features.snapshot_store import SnapshotStore
    import numpy as np

    _init_table()
    with sqlite3.connect(_db()) as conn:
        rows = conn.execute(
            "SELECT entity_id, value FROM graph_metrics WHERE metric='peer_community'").fetchall()
    if not rows:
        return {"available": False, "communities": []}
    members: dict[int, list[str]] = {}
    for eid, cid in rows:
        members.setdefault(int(cid), []).append(eid)

    # distinguishing features: top-3 by |z| vs firm mean, from persisted snapshots
    store = SnapshotStore()
    feat_rows: dict[str, dict] = {}
    for eid, _ in rows:
        snap = store.latest_for_entity("ADVISOR", eid)
        if isinstance(snap, dict) and snap.get("features"):
            feat_rows[eid] = {k: v for k, v in snap["features"].items()
                              if isinstance(v, (int, float)) and not isinstance(v, bool)}
    keys = sorted({k for f in feat_rows.values() for k in f})
    firm_mean = {k: np.mean([feat_rows[a].get(k, 0.0) for a in feat_rows]) for k in keys}
    firm_std = {k: (np.std([feat_rows[a].get(k, 0.0) for a in feat_rows]) or 1.0) for k in keys}

    out = []
    for cid, ids in sorted(members.items()):
        zc = {}
        for k in keys:
            vals = [feat_rows[a].get(k, 0.0) for a in ids if a in feat_rows]
            if vals:
                zc[k] = (np.mean(vals) - firm_mean[k]) / firm_std[k]
        top = sorted(zc.items(), key=lambda kv: -abs(kv[1]))[:3]
        out.append({
            "community_id": cid, "size": len(ids), "members": ids,
            "distinguishing_features": [
                {"feature": k, "z": round(float(z), 2), "direction": "higher" if z > 0 else "lower"}
                for k, z in top],
        })
    return {"available": True, "communities": out}
