from __future__ import annotations

from fastapi import APIRouter

from app.recommendations.lifecycle import RecommendationLifecycleService
from app.shared.responses import ok

router = APIRouter(prefix="/impact-ledger", tags=["Impact Ledger"])


@router.get("")
def ledger():
    """Section 13.2 — every completed recommendation's recorded consequence: the
    injected transaction, the impact amount (= the rec's own estimated impact), and
    the link back to its recommendation + advisor. Real rows from SQLite."""
    svc = RecommendationLifecycleService()
    entries = svc.ledger_entries()
    return ok(data={"entries": entries, "totals": svc.ledger_totals(entries)})


@router.get("/advisor/{advisor_id}")
def ledger_for_advisor(advisor_id: str):
    svc = RecommendationLifecycleService()
    entries = svc.ledger_entries(advisor_id)
    return ok(data={"entries": entries, "totals": svc.ledger_totals(entries)})


@router.get("/replay-report")
def replay_report():
    """Last boot's impact-ledger replay report (Section 13.2 durability evidence)."""
    return ok(data=RecommendationLifecycleService._last_replay)
