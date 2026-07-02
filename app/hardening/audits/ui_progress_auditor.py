from __future__ import annotations

from pathlib import Path


class UiProgressAuditor:
    REQUIRED_PAGES = [
        "enterprise_dashboard.py",
        "end_to_end_demo_run.py",
        "agentic_ai_console.py",
        "data_ingestion_sync.py",
        "feature_store.py",
        "embedding_similarity.py",
        "prediction_engine.py",
        "opportunity_engine.py",
        "recommendation_engine.py",
        "feedback_learning.py",
        "ai_assistant_chat.py",
        "final_audit.py",
        "runtime_validation.py",
        "graph_access_status.py",
    ]

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def audit(self) -> dict:
        pages_dir = self.root / "app/ui/pages"
        rows = []
        for page in self.REQUIRED_PAGES:
            path = pages_dir / page
            content = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
            has_status = "st.status" in content
            has_spinner = "st.spinner" in content
            has_progress = "st.progress" in content
            has_button = "st.button" in content
            # A page with no long-running button can still pass if it has no button.
            passed = path.exists() and ((has_status or has_spinner or has_progress) or not has_button)
            rows.append({
                "page": page,
                "exists": path.exists(),
                "has_status": has_status,
                "has_spinner": has_spinner,
                "has_progress": has_progress,
                "has_button": has_button,
                "status": "passed" if passed else "needs_progress_overlay",
            })
        failures = [r for r in rows if r["status"] != "passed"]
        return {
            "status": "passed" if not failures else "failed",
            "pages_checked": len(rows),
            "failures": failures,
            "pages": rows,
        }
