import csv
import json
import os
import tempfile
import time
from pathlib import Path

os.environ["MOCK_TIGERGRAPH"] = "true"

from app.config import settings
from app.services.ingestion_service import IngestionService
from app.services.manifest_service import ManifestService
from app.services.tigergraph_client import TigerGraphClient


def test_manifest_is_complete_and_nonempty():
    service = ManifestService()
    entries = service.entries()
    assert len(entries) == 182
    results = [service.inspect(entry) for entry in entries]
    assert all(result["exists"] for result in results)
    assert all(result["valid"] for result in results)
    assert all(result["actual_rows"] > 0 for result in results)
    assert sum(result["actual_rows"] for result in results) == 109328


def test_selection_includes_dependencies_and_preserves_order():
    service = ManifestService()
    edge = next(entry for entry in service.entries() if entry["kind"] == "edge")
    selected = service.resolve_selection([edge["file"]], include_dependencies=True)
    paths = [entry["file"] for entry in selected]
    assert edge["file"] in paths
    assert all(dep in paths for dep in edge["dependencies"])
    assert [entry["order"] for entry in selected] == sorted(entry["order"] for entry in selected)


def test_restpp_payload_uses_manifest_mappings():
    service = ManifestService()
    client = TigerGraphClient()
    vertex = next(entry for entry in service.entries() if entry["kind"] == "vertex")
    with service.resolve(vertex["file"]).open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    payload = client.build_payload(vertex, [row])
    vertex_id = row[vertex["id_column"]]
    assert vertex["target"] in payload["vertices"]
    assert vertex_id in payload["vertices"][vertex["target"]]
    assert vertex["id_column"] not in payload["vertices"][vertex["target"]][vertex_id]


def test_mock_upsert_reports_exact_acceptance():
    service = ManifestService()
    client = TigerGraphClient()
    for kind in ("vertex", "edge"):
        entry = next(item for item in service.entries() if item["kind"] == kind)
        with service.resolve(entry["file"]).open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))[:3]
        result = client.upsert(entry, rows)
        accepted = result["accepted_vertices"] if kind == "vertex" else result["accepted_edges"]
        assert accepted == len(rows)
        assert result["mock"] is True


def test_batch_failure_isolates_only_bad_row(monkeypatch):
    service = ManifestService()
    ingestion = IngestionService()
    entry = next(item for item in service.entries() if item["kind"] == "vertex")
    with service.resolve(entry["file"]).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))[:5]
    bad_key = rows[2][entry["id_column"]]

    def selective_upsert(current_entry, current_rows):
        if any(row[current_entry["id_column"]] == bad_key for row in current_rows):
            raise RuntimeError("simulated row rejection")
        return {"accepted_vertices": len(current_rows), "accepted_edges": 0, "mock": True}

    monkeypatch.setattr(ingestion.tg, "upsert", selective_upsert)
    succeeded, errors, response_log = ingestion._upsert_with_isolation(entry, rows, list(range(2, 7)))
    assert succeeded == 4
    assert len(errors) == 1
    assert errors[0][0] == 4
    assert errors[0][1][entry["id_column"]] == bad_key
    assert response_log


def test_fastapi_catalog_and_health_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert root.json()["version"] == "0.2.0"
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["tigergraph"]["mode"] == "mock"
        catalog = client.get("/api/v1/catalog/files")
        assert catalog.status_code == 200
        assert len(catalog.json()["files"]) == 182
        queries = client.get("/api/v1/catalog/queries")
        assert queries.status_code == 200
        assert len(queries.json()) == 43
