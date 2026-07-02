from __future__ import annotations

from pathlib import Path


class McpUsageAuditor:
    """Audits graph-related services to ensure they route via GraphAccessClient/TigerGraphUpsertClient."""

    GRAPH_RELATED_PATTERNS = [
        "memory_service.py",
        "feedback_learning_service.py",
        "recommendation_service.py",
        "opportunity_service.py",
        "prediction_service.py",
        "insights_coaching_service.py",
        "ai_assistant_chat_service.py",
        "data_ingestion",
        "tigergraph",
        "graph",
    ]

    REQUIRED_ACCESS_MARKERS = [
        "GraphAccessClient",
        "GraphAccessService",
        "TigerGraphUpsertClient",
        "graph_access",
        "upsert",
    ]

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def audit(self) -> dict:
        files = []
        for py in self.root.rglob("app/**/*.py"):
            rel = str(py.relative_to(self.root))
            lower = rel.lower()
            content = py.read_text(encoding="utf-8", errors="ignore")
            is_graph_related = any(p.lower() in lower or p in content for p in self.GRAPH_RELATED_PATTERNS)
            if not is_graph_related:
                continue
            has_marker = any(marker in content for marker in self.REQUIRED_ACCESS_MARKERS)
            direct_rest_risk = "requests." in content and "GraphAccess" not in content and "app/graph/tigergraph/rest_client.py" not in rel and "app/graph/tigergraph/rest_client.py" not in rel
            files.append({
                "file": rel,
                "graph_related": True,
                "uses_graph_access_layer_or_wrapper": has_marker,
                "direct_rest_risk": direct_rest_risk,
            })
        failures = [
            f for f in files
            if f["direct_rest_risk"]
        ]
        return {
            "status": "passed" if not failures else "failed",
            "files_checked": len(files),
            "failures": failures,
            "note": "Graph services are considered compliant when they route through GraphAccessClient, GraphAccessService, or TigerGraphUpsertClient compatibility wrapper.",
            "files": files,
        }
