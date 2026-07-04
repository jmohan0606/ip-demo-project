from __future__ import annotations

from fastapi import APIRouter

from app.revenue.analytics import RevenueAnalyticsService
from app.shared.responses import ok

router = APIRouter(prefix="/revenue", tags=["Revenue Analytics"])


@router.get("/analytics")
def analytics(scope_type: str = "FIRM", scope_id: str = "F001"):
    """Scope-aware revenue intelligence from real transactions: monthly trend,
    channel mix, per-child breakdown, KPIs."""
    return ok(data=RevenueAnalyticsService().analytics(scope_type=scope_type, scope_id=scope_id))
