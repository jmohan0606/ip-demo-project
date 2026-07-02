from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/llm/__init__.py",
    "app/llm/models.py",
    "app/llm/prompt_templates.py",
    "app/llm/azure_openai_adapter.py",
    "app/llm/mock_llm_adapter.py",
    "app/llm/llm_runtime.py",
    "app/agents/ai_assistant_runtime.py",
    "app/api/routers/llm_activation.py",
    "frontend/lib/api/llm-activation.ts",
    "frontend/components/llm-activation/llm-activation-workspace.tsx",
    "frontend/app/(dashboard)/llm-activation/page.tsx",
]
missing = [f for f in required if not (ROOT / f).exists()]
runtime_text = (ROOT / "app/llm/llm_runtime.py").read_text(encoding="utf-8")
assistant_text = (ROOT / "app/agents/ai_assistant_runtime.py").read_text(encoding="utf-8")
checks = {
    "azure_first": "AzureOpenAiAdapter" in runtime_text,
    "mock_fallback": "MockLlmAdapter" in runtime_text,
    "memory_grounding": "build_context_packet" in assistant_text,
    "memory_writeback": "write_memory" in assistant_text,
    "recommendation_narrative": "recommendation_narrative" in assistant_text,
}
report = {
    "status": "passed" if not missing and all(checks.values()) else "failed",
    "missing_files": missing,
    "validated_files": len(required) - len(missing),
    "required_files": len(required),
    "checks": checks,
}
out = ROOT / "docs/part_16_3_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
