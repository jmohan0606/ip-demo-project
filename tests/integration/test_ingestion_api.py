from fastapi.testclient import TestClient

from app.api.main import app


def test_ingestion_entities_api():
    client = TestClient(app)
    response = client.get("/ingestion/entities")
    assert response.status_code == 200
    data = response.json()["data"]
    assert any(e["entity_name"] == "advisor" for e in data)


def test_ingestion_batches_api():
    client = TestClient(app)
    response = client.get("/ingestion/batches")
    assert response.status_code == 200
    assert response.json()["success"] is True
