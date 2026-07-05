from __future__ import annotations

from fastapi import APIRouter

from app.revenue.analytics import RevenueAnalyticsService
from app.revenue.trend_explorer import RevenueTrendExplorerService
from app.shared.responses import ok

router = APIRouter(prefix="/revenue", tags=["Revenue Analytics"])


@router.get("/analytics")
def analytics(scope_type: str = "FIRM", scope_id: str = "F001", period: str = "ALL"):
    """Scope-aware revenue intelligence from real transactions: monthly trend,
    channel mix, per-child breakdown, KPIs."""
    return ok(data=RevenueAnalyticsService().analytics(scope_type=scope_type, scope_id=scope_id, period=period))


@router.get("/trend")
def trend(
    dimension: str = "division",
    granularity: str = "monthly",
    start: str | None = None,
    end: str | None = None,
    scope_type: str = "FIRM",
    scope_id: str = "F001",
):
    """Revenue Trend Explorer (9.6): per-period revenue sliced by a selectable
    dimension, with change vs the prior comparable period and an AI-generated
    driver summary grounded in the real per-period figures."""
    return ok(data=RevenueTrendExplorerService().trend(
        dimension=dimension, granularity=granularity, start=start, end=end,
        scope_type=scope_type, scope_id=scope_id,
    ))
