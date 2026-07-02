from __future__ import annotations

from pathlib import Path
import sys


def main() -> None:
    checks = {
        "python_3_11_plus": sys.version_info >= (3, 11),
        "pyproject_exists": Path("pyproject.toml").exists(),
        "env_example_exists": Path(".env.example").exists(),
        "enterprise_ui_exists": Path("app/ui/app_enterprise.py").exists(),
        "api_exists": Path("app/api/main.py").exists(),
        "sample_data_exists": Path("tigergraph/sample_data/demo_data_manifest.json").exists(),
        "docs_exist": Path("docs/README_OPERATIONS_INDEX.md").exists(),
    }
    failed = [k for k, v in checks.items() if not v]
    print("Installation readiness:")
    for k, v in checks.items():
        print(f"- {k}: {'PASS' if v else 'FAIL'}")
    if failed:
        raise SystemExit(f"Failed checks: {failed}")
    print("Installation readiness check passed.")


if __name__ == "__main__":
    main()
