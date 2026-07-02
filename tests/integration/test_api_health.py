from fastapi.testclient import TestClient
from app.api.main import app

def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["app_name"] == "iPerform Insights & Coaching"

def test_runtime_health_endpoint():
    client = TestClient(app)
    response = client.get("/health/runtime")
    assert response.status_code == 200
    body = response.json()
    assert body["application"] == "iPerform Insights & Coaching"
    assert body["graph_name"] == "iperform_insights_coaching_demo"
