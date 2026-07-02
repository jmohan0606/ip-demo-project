from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from ..config import settings

class ManifestService:
    def __init__(self):
        self.manifest_path = Path(settings.manifest_path).resolve()
        self.data_dir = Path(settings.sample_data_dir).resolve()
        self.schema_catalog_path = Path(settings.schema_catalog_path).resolve()

    def load(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def schema(self) -> dict:
        return json.loads(self.schema_catalog_path.read_text(encoding="utf-8"))

    def entries(self) -> list[dict]:
        return sorted(self.load()["files"], key=lambda x: (x["order"], x["file"]))

    def entry_map(self) -> dict[str, dict]:
        return {entry["file"]: entry for entry in self.entries()}

    def resolve_selection(self, selected: list[str] | None, include_dependencies: bool = True) -> list[dict]:
        entries = self.entry_map()
        if not selected:
            return self.entries()
        unknown = sorted(set(selected) - set(entries))
        if unknown:
            raise ValueError(f"Unknown manifest files: {unknown}")
        wanted = set(selected)
        if include_dependencies:
            pending = list(wanted)
            while pending:
                current = pending.pop()
                for dep in entries[current].get("dependencies", []):
                    if dep not in entries:
                        raise ValueError(f"Manifest dependency {dep!r} for {current!r} is missing")
                    if dep not in wanted:
                        wanted.add(dep)
                        pending.append(dep)
        return [entry for entry in self.entries() if entry["file"] in wanted]

    def resolve(self, rel_path: str) -> Path:
        p = (self.data_dir / rel_path).resolve()
        if p != self.data_dir and self.data_dir not in p.parents:
            raise ValueError("File path escapes sample data directory")
        return p

    def file_hash(self, rel_path: str) -> str:
        h = hashlib.sha256()
        with self.resolve(rel_path).open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def inspect(self, entry: dict) -> dict:
        p = self.resolve(entry["file"])
        headers: list[str] = []
        count = 0
        errors: list[str] = []
        if p.exists():
            with p.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for count, _ in enumerate(reader, 1):
                    pass
            missing = [c for c in entry.get("required_columns", []) if c not in headers]
            mapping_missing = [c for c in entry.get("columns", {}) if c not in headers]
            unexpected = [c for c in headers if c not in entry.get("columns", {})]
            if missing: errors.append(f"Missing required columns: {missing}")
            if mapping_missing: errors.append(f"Manifest columns not found in CSV: {mapping_missing}")
            if unexpected: errors.append(f"CSV columns not mapped by manifest: {unexpected}")
            if count == 0: errors.append("CSV has no data rows")
        else:
            errors.append("File not found")
        return {
            **entry,
            "exists": p.exists(),
            "headers": headers,
            "actual_rows": count,
            "hash": self.file_hash(entry["file"]) if p.exists() else None,
            "valid": not errors,
            "errors": errors,
        }

    def read_rows(self, entry: dict, start_row: int = 1):
        with self.resolve(entry["file"]).open(newline="", encoding="utf-8-sig") as f:
            for row_no, row in enumerate(csv.DictReader(f), 1):
                if row_no >= start_row:
                    yield row_no, row
