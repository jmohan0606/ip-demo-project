from fastapi.testclient import TestClient
from app.api.main import app


def test_demo_run_api():
    client = TestClient(app)
    response = client.post("/demo-run/full?advisor_id=ADV0001")
    assert response.status_code == 200
    assert response.json()["success"] is True
