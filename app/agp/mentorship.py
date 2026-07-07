from __future__ import annotations

from collections import defaultdict

from app.graph.client import get_graph_client
from app.graph.queries.common import advisor_transactions
from app.features.snapshot_store import SnapshotStore

"""Section 10 — AGP mentor/mentee pairing (GNN-similarity constrained matching) and
AGP program ROI (fair peer-baseline methodology).

Mentor pairing: mentees are enrolled advisors whose AGP risk band is at/above
"attention"; mentors are healthy, higher-producing advisors, ranked as candidates by
GNN embedding cosine similarity to the mentee (similar books coach best) with real
constraints: mentor capacity (≤2 mentees), mentor must meaningfully outperform the
mentee (≥1.2× LTM revenue), and mentors with a stronger referral-network position
(PageRank percentile) win ties. Greedy assignment on similarity, highest first.

Program ROI: for each enrolled advisor, production growth since their real
enrollment start date vs a FAIR peer baseline — the same calendar-window growth of
their GNN-most-similar NON-enrolled advisors. Comparing an enrollee against advisors
with similar books over the identical window isolates the program effect from
market-wide drift; small-sample caveats are stated, never hidden."""


def _cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5
    db = sum(y * y for y in b) ** 0.5
    return num / (da * db) if da and db else 0.0


class AgpMentorshipService:
    MENTOR_CAPACITY = 2
    OUTPERFORM_RATIO = 1.2

    def __init__(self) -> None:
        self._store = get_graph_client().store
        self._snaps = SnapshotStore()

    # ---- shared lookups -----------------------------------------------------
    def _features(self, advisor_id: str) -> dict:
        snap = self._snaps.latest_for_entity("ADVISOR", advisor_id)
        return (snap or {}).get("features", {}) if snap else {}

    def _name(self, advisor_id: str) -> str:
        return str((self._store.vertex("phx_dm_advisor", advisor_id) or {}).get("advisor_name") or advisor_id)

    def _enrollments(self) -> dict[str, dict]:
        """advisor_id -> enrollment attrs (ACTIVE only)."""
        out: dict[str, dict] = {}
        for aid in self._store.all_vertices("phx_dm_advisor"):
            for enr_id in self._store.out_ids("phx_dm_advisor_has_agp_enrollment", aid):
                attrs = self._store.vertex("phx_dm_agp_enrollment", enr_id) or {}
                if str(attrs.get("status")) == "ACTIVE":
                    out[aid] = attrs
        return out

    def _vectors(self) -> tuple[str, dict[str, list[float]]]:
        from app.ml import registry
        from app.ml.vector_client import get_vector_client
        vc = get_vector_client()
        model = registry.active_embedding_model()
        vecs: dict[str, list[float]] = {}
        for aid in self._store.all_vertices("phx_dm_advisor"):
            v = vc.get("ADVISOR", aid, model_name=model)
            if v is not None:
                vecs[aid] = v
        return model, vecs

    def _pagerank_pct(self, advisor_id: str) -> int | None:
        try:
            from app.ml import graph_algorithms as ga
            pos = ga.referral_position(advisor_id)
            return int(pos.get("percentile")) if pos.get("available") else None
        except Exception:
            return None

    # ---- mentor / mentee pairing -------------------------------------------
    def mentor_pairing(self) -> dict:
        enrollments = self._enrollments()
        feats = {aid: self._features(aid) for aid in self._store.all_vertices("phx_dm_advisor")}
        feats = {aid: f for aid, f in feats.items() if f}

        def risk(aid: str) -> float:
            v = feats.get(aid, {}).get("agp_risk_score")
            return float(v) if v is not None else 0.0

        def rev(aid: str) -> float:
            v = feats.get(aid, {}).get("revenue_ltm")
            return float(v) if v is not None else 0.0

        # Mentees: ACTIVE-enrolled advisors at/above the "attention" band (AGP-004: ≥40).
        mentees = sorted((a for a in enrollments if risk(a) >= 40), key=risk, reverse=True)
        # Mentors: healthy (on-track), with real production to teach from.
        mentor_pool = [a for a in feats if risk(a) < 40 and rev(a) > 0 and a not in mentees]

        model, vecs = self._vectors()
        pr_pct = {a: self._pagerank_pct(a) for a in mentor_pool}

        # Candidate edges: (similarity, mentor, mentee) under the outperform constraint.
        candidates: list[tuple[float, str, str]] = []
        for me in mentees:
            if me not in vecs:
                continue
            for mo in mentor_pool:
                if mo not in vecs or rev(mo) < self.OUTPERFORM_RATIO * rev(me):
                    continue
                sim = _cosine(vecs[me], vecs[mo])
                # tie-break bonus: referral-network position (strong hubs make better mentors)
                bonus = (pr_pct.get(mo) or 0) / 10000.0
                candidates.append((sim + bonus, mo, me))
        candidates.sort(reverse=True)

        load: dict[str, int] = defaultdict(int)
        assigned: dict[str, dict] = {}
        for score, mo, me in candidates:
            if me in assigned or load[mo] >= self.MENTOR_CAPACITY:
                continue
            load[mo] += 1
            sim = _cosine(vecs[me], vecs[mo])
            assigned[me] = {
                "mentee_id": me, "mentee_name": self._name(me),
                "mentee_risk": round(risk(me), 1), "mentee_revenue_ltm": round(rev(me), 2),
                "mentor_id": mo, "mentor_name": self._name(mo),
                "mentor_revenue_ltm": round(rev(mo), 2),
                "mentor_referral_percentile": pr_pct.get(mo),
                "similarity": round(sim, 4),
                "rationale": (
                    f"{self._name(mo)} runs the most similar book ({model} cosine {sim:.2f}) while "
                    f"outperforming on LTM revenue (${rev(mo):,.0f} vs ${rev(me):,.0f})"
                    + (f" and sits in the top {100 - pr_pct[mo]}% of the referral network"
                       if pr_pct.get(mo) is not None and pr_pct[mo] >= 50 else "")
                    + f" — a credible coach for a {'critical' if risk(me) >= 85 else 'at-risk'} mentee (risk {risk(me):.0f})."
                ),
            }

        unmatched = [
            {"mentee_id": m, "mentee_name": self._name(m), "mentee_risk": round(risk(m), 1),
             "reason": "no embedding vector" if m not in vecs else "no qualifying mentor with spare capacity"}
            for m in mentees if m not in assigned
        ]
        return {
            "model": model,
            "pairs": sorted(assigned.values(), key=lambda p: -p["mentee_risk"]),
            "unmatched": unmatched,
            "constraints": {
                "mentor_capacity": self.MENTOR_CAPACITY,
                "outperform_ratio": self.OUTPERFORM_RATIO,
                "mentee_rule": "ACTIVE AGP enrollment with agp_risk_score ≥ 40 (attention band or worse)",
                "mentor_rule": "on-track (risk < 40), revenue ≥ 1.2× mentee, ranked by GNN similarity + referral-hub bonus",
            },
            "methodology": (
                "Constrained greedy matching on GNN (GraphSAGE) embedding cosine similarity: similar books "
                "make transferable coaching. Constraints: each mentor takes at most "
                f"{self.MENTOR_CAPACITY} mentees and must out-produce the mentee by ≥{self.OUTPERFORM_RATIO}×; "
                "referral-network centrality (PageRank percentile) breaks ties toward natural connectors."
            ),
            "evidence": {
                "mentee_count": len(mentees), "mentor_pool": len(mentor_pool),
                "candidate_edges": len(candidates), "source": "GNN vectors + feature snapshots + AGP enrollments",
            },
        }

    # ---- program ROI ---------------------------------------------------------
    def _monthly_revenue(self, advisor_id: str) -> dict[str, float]:
        out: dict[str, float] = defaultdict(float)
        for _tx, attrs in advisor_transactions(self._store, [advisor_id]):
            m = str(attrs.get("transaction_date") or "")[:7]
            if m:
                out[m] += float(attrs.get("revenue_amount") or 0.0)
        return dict(out)

    @staticmethod
    def _window_avg(monthly: dict[str, float], months: list[str]) -> float | None:
        vals = [monthly.get(m) for m in months]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if len(vals) == len(months) and months else None

    @staticmethod
    def _shift(ym: str, delta: int) -> str:
        y, m = int(ym[:4]), int(ym[5:7])
        total = y * 12 + (m - 1) + delta
        return f"{total // 12:04d}-{total % 12 + 1:02d}"

    def program_roi(self, window: int = 3, peer_k: int = 5) -> dict:
        """Per-enrollee growth since enrollment vs the same-window growth of their
        GNN-most-similar NON-enrolled advisors (the fair baseline)."""
        enrollments = self._enrollments()
        model, vecs = self._vectors()
        monthly_cache: dict[str, dict[str, float]] = {}

        def monthly(aid: str) -> dict[str, float]:
            if aid not in monthly_cache:
                monthly_cache[aid] = self._monthly_revenue(aid)
            return monthly_cache[aid]

        # last fully-populated data month across the dataset
        all_months = sorted({m for aid in enrollments for m in monthly(aid)})
        if not all_months:
            return {"available": False, "note": "no transaction months found"}
        latest = all_months[-1]

        non_enrolled = [a for a in self._store.all_vertices("phx_dm_advisor")
                        if a not in enrollments and a in vecs]

        rows = []
        for aid, enr in enrollments.items():
            start = str(enr.get("start_date") or "")[:7]
            if not start or aid not in vecs:
                continue
            pre = [self._shift(start, -i) for i in range(1, window + 1)][::-1]   # window before enrollment
            post = [self._shift(latest, -i) for i in range(0, window)][::-1]     # latest window
            base = self._window_avg(monthly(aid), pre)
            now = self._window_avg(monthly(aid), post)
            if not base or now is None:
                continue
            growth = (now - base) / base * 100.0

            peers = sorted(non_enrolled, key=lambda p: -_cosine(vecs[aid], vecs[p]))[:peer_k]
            peer_growths = []
            for p in peers:
                pb = self._window_avg(monthly(p), pre)
                pn = self._window_avg(monthly(p), post)
                if pb and pn is not None:
                    peer_growths.append((pn - pb) / pb * 100.0)
            baseline = sum(peer_growths) / len(peer_growths) if peer_growths else None
            rows.append({
                "advisor_id": aid, "advisor_name": self._name(aid),
                "cohort": enr.get("cohort"), "enrolled_since": enr.get("start_date"),
                "program_month": enr.get("current_program_month"),
                "growth_pct": round(growth, 1),
                "peer_baseline_pct": round(baseline, 1) if baseline is not None else None,
                "uplift_pp": round(growth - baseline, 1) if baseline is not None else None,
                "peer_group": [{"advisor_id": p, "advisor_name": self._name(p),
                                "similarity": round(_cosine(vecs[aid], vecs[p]), 3)} for p in peers],
            })

        with_uplift = [r for r in rows if r["uplift_pp"] is not None]
        avg_uplift = round(sum(r["uplift_pp"] for r in with_uplift) / len(with_uplift), 1) if with_uplift else None
        positive = sum(1 for r in with_uplift if r["uplift_pp"] > 0)
        return {
            "available": True,
            "model": model,
            "window_months": window,
            "latest_data_month": latest,
            "rows": sorted(rows, key=lambda r: -(r["uplift_pp"] if r["uplift_pp"] is not None else -999)),
            "summary": {
                "enrolled_measured": len(with_uplift),
                "avg_uplift_pp": avg_uplift,
                "outperforming_baseline": positive,
                "share_outperforming_pct": round(positive / len(with_uplift) * 100) if with_uplift else None,
            },
            "methodology": (
                f"For each ACTIVE enrollee: average monthly revenue over the last {window} data months vs the "
                f"{window} months before their real enrollment date → growth %. Fair baseline = the same two "
                f"calendar windows measured on their {peer_k} GNN-most-similar NON-enrolled advisors "
                "(similar books, identical market window — isolates the program effect from market drift). "
                "Uplift = enrollee growth − peer baseline, in percentage points."
            ),
            "caveats": (
                "Demo-scale sample (24 enrollees, 60 advisors): directional evidence, not a causal study. "
                "Peer baselines from ≤5 similar advisors are noisy; enrollees whose enrollment predates the "
                "transaction history are excluded rather than approximated."
            ),
        }
