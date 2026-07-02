from fastapi.testclient import TestClient
from app.api.main import app


def test_graph_access_health_api():
    client = TestClient(app)
    response = client.get("/graph-access/health")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_graph_access_schema_api():
    client = TestClient(app)
    response = client.get("/graph-access/schema")
    assert response.status_code == 200
    assert response.json()["success"] is True
