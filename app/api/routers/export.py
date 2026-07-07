from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.export.dashboard_export import build_pdf, build_pptx

router = APIRouter(prefix="/export", tags=["Export"])

_MEDIA = {
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


@router.get("/dashboard")
def export_dashboard(
    scope_type: str = "FIRM",
    scope_id: str = "F001",
    period: str = "LTM",
    compare_to: str = "Prior Year",
    format: str = Query("pdf", pattern="^(pdf|pptx)$"),
):
    """Export the executive dashboard view for the given scope/period to PDF or PPTX.
    Real data — the same rollup the screen renders. Returns a downloadable file."""
    if format == "pptx":
        content = build_pptx(scope_type, scope_id, period, compare_to)
    else:
        content = build_pdf(scope_type, scope_id, period, compare_to)
    filename = f"iperform_{scope_type}_{scope_id}_{period}.{format}".lower()
    return Response(
        content=content,
        media_type=_MEDIA[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
