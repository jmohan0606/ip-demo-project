from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ".env.example",
    "frontend/.env.local.example",
    "uv.toml.example",
    "frontend/.npmrc.example",
    ".gitignore",
    ".dockerignore",
    "app/config/runtime_config.py",
    "app/config/__init__.py",
    "app/api/routers/config_status.py",
    "frontend/lib/api/config.ts",
]

UNWANTED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "node_modules",
    "playwright-report",
    "test-results",
}

UNWANTED_FILE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".bak"}


def main() -> None:
    missing = [item for item in REQUIRED_FILES if not (ROOT / item).exists()]
    unwanted_dirs = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.is_dir() and path.name in UNWANTED_DIR_NAMES
    ]
    unwanted_files = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.is_file() and (path.suffix in UNWANTED_FILE_SUFFIXES or path.name == ".DS_Store")
    ]

    report = {
        "status": "passed" if not missing and not unwanted_dirs and not unwanted_files else "failed",
        "missing_required_files": missing,
        "unwanted_dirs": unwanted_dirs,
        "unwanted_files": unwanted_files,
        "required_files_validated": len(REQUIRED_FILES) - len(missing),
    }

    out = ROOT / "docs/project_cleanup_validation_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
