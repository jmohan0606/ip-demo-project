from fastapi.testclient import TestClient
from app.api.main import app


def test_recommendation_counts_api():
    client = TestClient(app)
    response = client.get("/recommendations/counts")
    assert response.status_code == 200
    assert response.json()["success"] is True
