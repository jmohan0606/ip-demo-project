from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/knowledge/__init__.py",
    "app/knowledge/models.py",
    "app/knowledge/chunker.py",
    "app/knowledge/embedding_provider.py",
    "app/knowledge/chroma_adapter.py",
    "app/knowledge/mock_vector_store.py",
    "app/knowledge/knowledge_runtime.py",
    "app/api/routers/knowledge_runtime.py",
    "frontend/lib/api/knowledge-runtime.ts",
    "frontend/components/knowledge-runtime/knowledge-runtime-workspace.tsx",
    "frontend/app/(dashboard)/knowledge-runtime/page.tsx",
]
missing = [f for f in required if not (ROOT / f).exists()]
runtime_text = (ROOT / "app/knowledge/knowledge_runtime.py").read_text(encoding="utf-8")
checks = {
    "chroma_adapter_used": "ChromaAdapter" in runtime_text,
    "mock_fallback_used": "MockPersistentVectorStore" in runtime_text,
    "graph_lineage_used": "get_graph_runtime" in runtime_text,
    "chunker_used": "DocumentChunker" in runtime_text,
}
report = {
    "status": "passed" if not missing and all(checks.values()) else "failed",
    "missing_files": missing,
    "validated_files": len(required) - len(missing),
    "required_files": len(required),
    "checks": checks,
}
out = ROOT / "docs/part_15_5_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
