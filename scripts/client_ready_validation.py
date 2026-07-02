from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.audit.package_auditor import PackageAuditor
from app.services.agentic_ai_service import AgenticAiService
from app.agents.state.agent_state import AgenticRequest
from app.services.graph_access_service import GraphAccessService


def main() -> None:
    audit = PackageAuditor(".").write_reports()
    assert audit["python_compile"]["status"] == "passed", audit["python_compile"]["errors"]
    assert audit["sqlite"]["status"] == "passed", audit["sqlite"]
    assert audit["chroma"]["status"] == "passed", audit["chroma"]

    graph_health = GraphAccessService().health()
    assert graph_health["active_mode"] in {"mcp", "rest", "mock", "unavailable"}

    agent_response = AgenticAiService().run(
        AgenticRequest(
            question="Why is my revenue low and what should I do next?",
            persona="Advisor",
            scope_type="Advisor",
            scope_id="ADV0001",
            requested_capabilities=["prediction", "opportunity", "recommendation"],
            write_to_tigergraph=False,
        )
    )
    assert agent_response.answer
    assert agent_response.tasks
    assert agent_response.evidence

    db = Path("data/sqlite/iperform.db")
    conn = sqlite3.connect(db)
    rec_count = conn.execute("SELECT COUNT(*) FROM phx_dm_local_recommendation").fetchone()[0]
    mem_count = conn.execute("SELECT COUNT(*) FROM phx_dm_local_context_memory").fetchone()[0]
    conn.close()
    assert rec_count > 0
    assert mem_count > 0

    result = {
        "client_ready_validation": "passed",
        "graph_active_mode": graph_health["active_mode"],
        "agent_tasks": len(agent_response.tasks),
        "agent_evidence": len(agent_response.evidence),
        "recommendations": rec_count,
        "memories": mem_count,
        "audit_summary": audit["summary"],
    }
    Path("docs/final_audit/client_ready_validation_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
