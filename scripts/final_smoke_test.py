from __future__ import annotations

import json
from pathlib import Path
import py_compile

from app.config.settings import get_settings
from app.services.demo_orchestration_service import DemoOrchestrationService
from app.services.graph_access_service import GraphAccessService


def compile_all() -> tuple[int, list[dict]]:
    errors = []
    compiled = 0
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".venv" in str(py_file):
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
            compiled += 1
        except Exception as exc:
            errors.append({"file": str(py_file), "error": str(exc)})
    return compiled, errors


def main() -> None:
    required = [
        "pyproject.toml",
        "README.md",
        ".env.example",
        "app/api/main.py",
        "app/ui/app_enterprise.py",
        "run_local_api.py",
        "tigergraph/schema/01_vertices.gsql",
        "tigergraph/schema/02_edges.gsql",
        "tigergraph/schema/03_create_graph.gsql",
        "tigergraph/sample_data/demo_data_manifest.json",
        "runbooks/quick_start.md",
    ]
    for file in required:
        assert Path(file).exists(), f"Missing required file: {file}"

    settings = get_settings()
    assert settings.tigergraph_graph == "iperform_insights_coaching_demo"
    assert settings.tigergraph_schema_prefix == "phx_dm_"

    compiled, errors = compile_all()
    assert not errors, json.dumps(errors, indent=2)

    graph_health = GraphAccessService().health()
    assert graph_health["active_mode"] in {"mcp", "rest", "mock", "unavailable"}

    result = DemoOrchestrationService().run_full_demo("ADV0001")
    assert result.status == "completed", result.model_dump()
    assert result.summary["insight_cards"] > 0

    print("Final consolidated smoke test passed.")
    print(f"Compiled Python files: {compiled}")
    print(json.dumps(result.summary, indent=2))


if __name__ == "__main__":
    main()
