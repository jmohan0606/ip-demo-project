from __future__ import annotations

from fastapi import APIRouter

from app.scope.rollup import ScopeRollupService
from app.shared.responses import ok

router = APIRouter(prefix="/scope", tags=["Scope Rollup"])


@router.get("/summary")
def summary(scope_type: str = "FIRM", scope_id: str = "F001"):
    """Scope-aware rollup: aggregates every advisor's real feature snapshot under
    the given scope up to totals + one-level child breakdown + top advisors. The
    aggregation primitive behind scope-adaptive leadership pages."""
    return ok(data=ScopeRollupService().summary(scope_type=scope_type, scope_id=scope_id))
