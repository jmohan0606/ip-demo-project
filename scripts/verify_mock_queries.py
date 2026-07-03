"""Run every GQ-### case from the foundation package's query contract against
MockGraphClient and check (a) all expected output keys are present when they are
literal key lists, (b) every required_result_key is present and non-empty.

Usage: python scripts/verify_mock_queries.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph.client import MockGraphClient  # noqa: E402


def main() -> int:
    cases = json.loads(
        Path("docs/tigergraph_foundation/tests/query_cases.json").read_text(encoding="utf-8")
    )["cases"]
    client = MockGraphClient()
    failures: list[str] = []
    empty_required: list[str] = []

    for case in cases:
        name = case["query_name"]
        try:
            response = client.run_query(name, case["params"])
        except Exception as exc:
            failures.append(f"{case['id']} {name}: raised {exc}")
            continue
        results = response.get("results", [])
        merged: dict = {}
        for entry in results:
            merged.update(entry)
        for key in case.get("required_result_keys", []):
            if key not in merged:
                failures.append(f"{case['id']} {name}: missing required key '{key}' (has {sorted(merged)[:8]}...)")
            elif merged[key] in ([], {}, None, 0, 0.0):
                empty_required.append(f"{case['id']} {name}: required key '{key}' is empty ({merged[key]!r})")

    print(f"cases: {len(cases)}  hard failures: {len(failures)}  empty-required: {len(empty_required)}")
    for f in failures:
        print("FAIL", f)
    for w in empty_required:
        print("EMPTY", w)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
