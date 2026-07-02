from __future__ import annotations

import csv
from pathlib import Path


class DemoCsvLoader:
    def __init__(self) -> None:
        self.sample_data_dir = Path("tigergraph/sample_data")

    def read_csv(self, file_name: str) -> list[dict]:
        path = self.sample_data_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing demo CSV: {path}")
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))
