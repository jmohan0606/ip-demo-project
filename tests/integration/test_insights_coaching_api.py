from fastapi.testclient import TestClient
from app.api.main import app


def test_insights_counts_api():
    client = TestClient(app)
    response = client.get("/insights-coaching/counts")
    assert response.status_code == 200
    assert response.json()["success"] is True
