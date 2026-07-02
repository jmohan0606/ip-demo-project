from fastapi.testclient import TestClient
from app.api.main import app


def test_runtime_validation_api():
    client = TestClient(app)
    response = client.get("/runtime-validation/run")
    assert response.status_code == 200
    assert response.json()["success"] is True
