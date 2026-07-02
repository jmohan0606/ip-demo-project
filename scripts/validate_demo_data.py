from __future__ import annotations

import csv
import json
from pathlib import Path


def count_rows(path: Path) -> int:
    with path.open(encoding="utf-8") as f:
        return max(0, sum(1 for _ in f) - 1)


def main() -> None:
    base = Path("tigergraph/sample_data")
    manifest = json.loads((base / "demo_data_manifest.json").read_text(encoding="utf-8"))
    required = [
        "phx_dm_advisor.csv",
        "phx_dm_household.csv",
        "phx_dm_account.csv",
        "phx_dm_transaction.csv",
        "phx_dm_crm_activity.csv",
        "phx_dm_prediction_result.csv",
        "phx_dm_recommendation.csv",
        "phx_dm_context_memory.csv",
        "phx_dm_feature_snapshot.csv",
    ]
    for file in required:
        path = base / file
        assert path.exists(), f"Missing {file}"
        assert count_rows(path) > 0, f"No rows in {file}"

    assert manifest["scale"]["advisors"] >= 150
    assert manifest["scale"]["households"] >= 2000
    assert manifest["scale"]["accounts"] >= 5000
    assert manifest["scale"]["transactions"] >= 100000

    print("Enterprise demo data validation passed.")
    print(json.dumps(manifest["scale"], indent=2))


if __name__ == "__main__":
    main()
