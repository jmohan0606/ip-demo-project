from __future__ import annotations

import subprocess
import sys


def main() -> None:
    print("Preloaded DBs are already included in this package.")
    print("Validate with: uv run python scripts/validate_preloaded_demo_databases.py")


if __name__ == "__main__":
    main()
