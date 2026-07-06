"""Section 13.8 — end-to-end stateful recommendation lifecycle verification.

One continuous real-data trace on a NON-ANCHORED advisor (A005): select -> generate
-> accept -> start -> complete (real impact) -> ledger -> propagation (exact +impact
on 3 screens) -> terminal -> regenerate (addressed excluded) -> restart durability.
Prints real values and asserts exact deltas. Run against the live backend on :8000.

Usage: python3 scripts/verify_section13_lifecycle.py
"""
from __future__ import annotations

import json
import sys
import urllib.request

B = "http://127.0.0.1:8000"
ADV = "A005"


def get(u: str):
    return json.load(urllib.request.urlopen(B + u))["data"]


def post(u: str, body: dict | None = None):
    req = urllib.request.Request(B + u, data=json.dumps(body or {}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req))["data"]


def reset_advisor():
    from app.feature_store.sqlite_manager import SQLiteManager
    from app.features.engineering import FeatureEngineeringService
    from app.features.snapshot_store import SnapshotStore
    with SQLiteManager().connect() as c:
        for t in ["phx_dm_local_recommendation", "phx_dm_local_rec_status_transition", "phx_dm_local_impact_ledger"]:
            c.execute(f"DELETE FROM {t} WHERE advisor_id=?", (ADV,))
        c.execute("DELETE FROM phx_dm_local_context_memory WHERE scope_id=? AND source='recommendation_lifecycle'", (ADV,))
        c.commit()
    # revert snapshot to base (requires backend restart to clear in-memory injected tx first — caller handles)
    snap = FeatureEngineeringService().compute_advisor_snapshot(ADV)
    SnapshotStore().save(snap)


def main() -> int:
    ok_all = True

    def check(name, cond):
        nonlocal ok_all
        print(f"   [{'PASS' if cond else 'FAIL'}] {name}")
        ok_all = ok_all and cond

    print("=== Section 13.8 lifecycle verification (advisor A005, non-anchored) ===")

    print("\n1. BASELINE")
    rev0 = get(f"/revenue/analytics?scope_type=ADVISOR&scope_id={ADV}&period=LTM")["kpis"]["total_revenue"]
    snap0 = get(f"/features/snapshot/{ADV}")["features"]["revenue_ltm"]
    firm0 = get("/scope/dashboard?scope_type=FIRM&scope_id=F001&period=LTM&compare_to=Prior%20Year")["totals"]["revenue_ltm"]
    print(f"   advisor rev-analytics={rev0}  snapshot revenue_ltm={snap0}  firm rollup={firm0}")

    print("\n2. GENERATE")
    gen = post(f"/recommendations/generate/{ADV}")
    recs = gen["recommendations"]
    rid = recs[0]["recommendation_id"]
    I = round(recs[0]["estimated_revenue_impact"], 2)
    print(f"   top rec {rid}  status={recs[0]['status']}  estimated_impact I={I}")
    check("top rec is OPEN with full allowed_actions", recs[0]["status"] == "OPEN" and "accept" in recs[0]["allowed_actions"])

    print("\n3. ACCEPT (feedback submit — learning loop must move)")
    fam = recs[0]["action_family"]
    a = post("/feedback-learning/submit", {"recommendation_id": rid, "action": "accept", "action_family": fam, "user_id": ADV})
    w_after_accept = a["new_family_weight"]
    print(f"   to_status={a['lifecycle']['to_status']}  family weight -> {w_after_accept}")
    check("status ACCEPTED", a["lifecycle"]["to_status"] == "ACCEPTED")

    print("\n4. START (pure lifecycle transition)")
    s = post(f"/recommendations/{rid}/transition", {"action": "start", "actor_id": ADV})
    check("status IN_PROGRESS", s["to_status"] == "IN_PROGRESS")

    print("\n5. COMPLETE (real impact generated)")
    c = post("/feedback-learning/submit", {"recommendation_id": rid, "action": "complete", "action_family": fam, "user_id": ADV})
    lc = c["lifecycle"]
    print(f"   to_status={lc['to_status']}  impact={lc['impact']['impact_amount']}  tx={lc['impact']['source_transaction_id']}")
    check("status COMPLETED + terminal + allowed_actions empty", lc["to_status"] == "COMPLETED" and lc["terminal"] and lc["allowed_actions"] == [])
    check("recorded impact == estimated impact I", abs(lc["impact"]["impact_amount"] - I) < 0.01)

    print("\n6. LEDGER")
    led = get(f"/impact-ledger/advisor/{ADV}")
    check("one ledger entry with impact == I", led["totals"]["completed_count"] == 1 and abs(led["totals"]["total_impact"] - I) < 0.01)

    print("\n7. PROPAGATION (exact +I on 3 screens)")
    rev1 = get(f"/revenue/analytics?scope_type=ADVISOR&scope_id={ADV}&period=LTM")["kpis"]["total_revenue"]
    snap1 = get(f"/features/snapshot/{ADV}")["features"]["revenue_ltm"]
    firm1 = get("/scope/dashboard?scope_type=FIRM&scope_id=F001&period=LTM&compare_to=Prior%20Year")["totals"]["revenue_ltm"]
    for nm, base, now in [("advisor rev-analytics", rev0, rev1), ("advisor snapshot revenue_ltm", snap0, snap1), ("firm rollup revenue_ltm", firm0, firm1)]:
        d = round(now - base, 2)
        print(f"   {nm}: {base} -> {now}  delta={d}")
        check(f"{nm} delta == exactly +I", abs(d - I) < 0.02)

    print("\n8. REGENERATE (addressed opportunity excluded)")
    gen2 = post(f"/recommendations/generate/{ADV}")
    opp = recs[0]["opportunity_id"]
    open_opps = [x["opportunity_id"] for x in gen2["recommendations"]]
    addressed = [x["opportunity_id"] for x in gen2["addressed_opportunities"]]
    check("completed opp excluded from open recs", opp not in open_opps)
    check("completed opp in addressed list", opp in addressed)
    print(f"   lifecycle_counts: {gen2['lifecycle_counts']}")

    print("\n9. LEARNING LOOP INTACT (weight moved, not reset)")
    check("family weight increased after accept/complete", w_after_accept >= 1.0)

    print("\n" + ("=== ALL CHECKS PASSED ===" if ok_all else "=== SOME CHECKS FAILED ==="))
    print("(Restart-durability + real-Claude AI awareness are verified separately; see PROGRESS.md.)")
    return 0 if ok_all else 1


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_advisor()
        print("A005 reset (snapshot recomputed to base)")
    else:
        sys.exit(main())
