from __future__ import annotations

from fastapi import APIRouter

from app.scope.rollup import ScopeRollupService
from app.scope.dashboard import ScopeDashboardService
from app.scope.insight import ScopeInsightService
from app.shared.responses import ok

router = APIRouter(prefix="/scope", tags=["Scope Rollup"])


@router.get("/summary")
def summary(scope_type: str = "FIRM", scope_id: str = "F001"):
    """Scope-aware rollup: aggregates every advisor's real feature snapshot under
    the given scope up to totals + one-level child breakdown + top advisors. The
    aggregation primitive behind scope-adaptive leadership pages."""
    return ok(data=ScopeRollupService().summary(scope_type=scope_type, scope_id=scope_id))


@router.get("/dashboard")
def dashboard(scope_type: str = "FIRM", scope_id: str = "F001",
              period: str = "LTM", compare_to: str = "Prior Year"):
    """Everything the Executive Dashboard needs in one period-aware, scope-aware,
    Compare-To-aware payload (12.1): rollup totals + status + top/bottom advisors,
    period-windowed revenue trend / product-category / channel / YoY drivers /
    geography, top & bottom markets, a peer benchmark, and a headline whose delta
    respects the Compare-To control. All values are real sums/means — no hardcoding."""
    return ok(data=ScopeDashboardService().dashboard(
        scope_type=scope_type, scope_id=scope_id, period=period, compare_to=compare_to))


@router.get("/ai-insight")
def ai_insight(scope_type: str = "FIRM", scope_id: str = "F001",
               period: str = "LTM", compare_to: str = "Prior Year", persona: str = "Advisor"):
    """Scope-level AI Insight Summary (Key Drivers / Watch Outs / What to Monitor),
    every element derived from the real scope+period numbers; the LLM writes only the
    grounded executive-summary narrative. Wire LLM_CLIENT_MODE=claude for real prose."""
    return ok(data=ScopeInsightService().insight(
        scope_type=scope_type, scope_id=scope_id, period=period, compare_to=compare_to, persona=persona))
