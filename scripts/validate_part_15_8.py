from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/memory/__init__.py",
    "app/memory/models.py",
    "app/memory/memory_store.py",
    "app/memory/context_engineering.py",
    "app/memory/memory_runtime.py",
    "app/api/routers/memory_runtime.py",
    "frontend/lib/api/memory-runtime.ts",
    "frontend/components/memory-runtime/memory-runtime-workspace.tsx",
    "frontend/app/(dashboard)/memory-runtime/page.tsx",
]
missing = [f for f in required if not (ROOT / f).exists()]
runtime_text = (ROOT / "app/memory/memory_runtime.py").read_text(encoding="utf-8")
checks = {
    "sqlite_memory_store": "SQLiteMemoryStore" in runtime_text,
    "context_engineering": "ContextEngineeringService" in runtime_text,
    "knowledge_runtime": "get_knowledge_runtime" in runtime_text,
    "graph_runtime": "get_graph_runtime" in runtime_text,
    "context_packet": "ContextPacket" in runtime_text,
}
report = {
    "status": "passed" if not missing and all(checks.values()) else "failed",
    "missing_files": missing,
    "validated_files": len(required) - len(missing),
    "required_files": len(required),
    "checks": checks,
}
out = ROOT / "docs/part_15_8_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
