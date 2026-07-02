from __future__ import annotations

import json
from pathlib import Path


class DemoDataCatalogService:
    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]
        self.sample_data_dir = self.project_root / "tigergraph" / "sample_data"

    def manifest(self) -> dict:
        manifest_file = self.sample_data_dir / "demo_data_manifest.json"
        return json.loads(manifest_file.read_text(encoding="utf-8"))

    def list_csv_files(self) -> list[dict]:
        files = []
        for csv_file in sorted(self.sample_data_dir.glob("*.csv")):
            with csv_file.open(encoding="utf-8") as f:
                row_count = max(0, sum(1 for _ in f) - 1)
            files.append({
                "file_name": csv_file.name,
                "relative_path": str(csv_file.relative_to(self.project_root)),
                "row_count": row_count,
            })
        return files
