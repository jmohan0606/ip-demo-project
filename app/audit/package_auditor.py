from __future__ import annotations

import json
import py_compile
import sqlite3
from pathlib import Path

from app.audit.requirement_catalog import REQUIREMENT_CATALOG


class PackageAuditor:
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)

    def run_all(self) -> dict:
        return {
            "python_compile": self.compile_python(),
            "requirements": self.validate_requirements(),
            "sqlite": self.validate_sqlite(),
            "chroma": self.validate_chroma(),
            "ui": self.validate_ui(),
            "graph_access": self.validate_graph_access_artifacts(),
            "summary": {},
        }

    def compile_python(self) -> dict:
        compiled = 0
        errors = []
        for py_file in self.root.rglob("*.py"):
            if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                continue
            try:
                py_compile.compile(str(py_file), doraise=True)
                compiled += 1
            except Exception as exc:
                errors.append({"file": str(py_file.relative_to(self.root)), "error": str(exc)})
        return {"compiled": compiled, "errors": errors, "status": "passed" if not errors else "failed"}

    def validate_requirements(self) -> list[dict]:
        results = []
        for req in REQUIREMENT_CATALOG:
            artifacts = req["artifacts"]
            missing = [a for a in artifacts if not (self.root / a).exists()]
            status = "passed" if not missing else "failed"
            detail = "All required artifacts exist." if not missing else f"Missing: {missing}"

            if status == "passed":
                validation = req.get("validation")
                if validation == "contains_phx_prefix":
                    content = "\n".join((self.root / a).read_text(encoding="utf-8", errors="ignore") for a in artifacts if (self.root / a).exists())
                    status = "passed" if "phx_dm_" in content else "failed"
                    detail = "phx_dm_ prefix found." if status == "passed" else "phx_dm_ prefix not found."
                elif validation == "contains_langgraph_langchain":
                    content = (self.root / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
                    status = "passed" if "langgraph" in content.lower() and "langchain" in content.lower() else "failed"
                    detail = "LangGraph/LangChain dependencies found." if status == "passed" else "Missing LangGraph/LangChain dependency."
                elif validation == "contains_persona_scope":
                    content = "\n".join((self.root / a).read_text(encoding="utf-8", errors="ignore") for a in artifacts)
                    status = "passed" if "Persona" in content and "Scope" in content else "failed"
                    detail = "Persona and Scope controls found." if status == "passed" else "Persona/Scope controls not found."
                elif validation == "sqlite_populated":
                    db = self.root / artifacts[0]
                    status = "passed" if db.exists() and db.stat().st_size > 0 else "failed"
                    detail = f"SQLite size={db.stat().st_size if db.exists() else 0}"

            results.append({
                "id": req["id"],
                "requirement": req["requirement"],
                "priority": req["priority"],
                "status": status,
                "detail": detail,
                "artifacts": artifacts,
            })
        return results

    def validate_sqlite(self) -> dict:
        db = self.root / "data/sqlite/iperform.db"
        if not db.exists():
            return {"status": "failed", "error": "data/sqlite/iperform.db missing"}
        required_tables = [
            "phx_dm_feature_vector",
            "phx_dm_local_prediction_result",
            "phx_dm_local_opportunity",
            "phx_dm_local_recommendation",
            "phx_dm_local_context_memory",
            "phx_dm_knowledge_document_catalog",
            "phx_dm_local_chat_turn",
        ]
        counts = {}
        errors = []
        conn = sqlite3.connect(db)
        try:
            for table in required_tables:
                try:
                    counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    if counts[table] <= 0:
                        errors.append(f"{table} is empty")
                except Exception as exc:
                    errors.append(f"{table}: {exc}")
        finally:
            conn.close()
        return {"status": "passed" if not errors else "failed", "counts": counts, "errors": errors, "size_bytes": db.stat().st_size}

    def validate_chroma(self) -> dict:
        chroma = self.root / "data/chroma"
        manifest = chroma / "preloaded_chroma_manifest.json"
        index = chroma / "preloaded_knowledge_index.json"
        return {
            "status": "passed" if chroma.exists() and manifest.exists() and index.exists() else "failed",
            "path_exists": chroma.exists(),
            "manifest_exists": manifest.exists(),
            "index_exists": index.exists(),
        }

    def validate_ui(self) -> dict:
        pages = list((self.root / "app/ui/pages").glob("*.py")) if (self.root / "app/ui/pages").exists() else []
        required = [
            "enterprise_dashboard.py",
            "agentic_ai_console.py",
            "ai_assistant_chat.py",
            "graph_access_status.py",
            "feedback_learning.py",
            "recommendation_engine.py",
        ]
        existing = {p.name for p in pages}
        missing = [p for p in required if p not in existing]
        return {"status": "passed" if not missing else "failed", "page_count": len(pages), "missing": missing}

    def validate_graph_access_artifacts(self) -> dict:
        files = [
            "app/graph/access/graph_access_client.py",
            "app/graph/tigergraph/mcp_library_client.py",
            "app/graph/tigergraph/mcp_client.py",
            "app/graph/tigergraph/rest_client.py",
            "app/graph/mock/mock_graph_data_service.py",
        ]
        missing = [f for f in files if not (self.root / f).exists()]
        return {
            "status": "passed" if not missing else "failed",
            "missing": missing,
            "fallback_order": "MCP library -> MCP legacy -> REST -> Mock",
        }

    def write_reports(self, output_dir: str | Path = "docs/final_audit") -> dict:
        out = self.root / output_dir
        out.mkdir(parents=True, exist_ok=True)
        report = self.run_all()
        reqs = report["requirements"]
        passed = sum(1 for r in reqs if r["status"] == "passed")
        failed = sum(1 for r in reqs if r["status"] != "passed")
        report["summary"] = {
            "requirement_count": len(reqs),
            "requirements_passed": passed,
            "requirements_failed": failed,
            "python_compile_status": report["python_compile"]["status"],
            "sqlite_status": report["sqlite"]["status"],
            "chroma_status": report["chroma"]["status"],
            "ui_status": report["ui"]["status"],
            "graph_access_status": report["graph_access"]["status"],
            "overall_status": "passed" if failed == 0 and report["python_compile"]["status"] == "passed" else "review_needed",
        }
        (out / "final_audit_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (out / "requirement_traceability_audit.json").write_text(json.dumps(reqs, indent=2), encoding="utf-8")
        return report
