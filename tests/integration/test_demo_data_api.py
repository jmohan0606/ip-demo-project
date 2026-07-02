from fastapi.testclient import TestClient

from app.api.main import app


def test_demo_data_manifest_api():
    client = TestClient(app)
    response = client.get("/demo-data/manifest")
    assert response.status_code == 200
    assert response.json()["data"]["scale"]["advisors"] >= 150


def test_demo_data_files_api():
    client = TestClient(app)
    response = client.get("/demo-data/files")
    assert response.status_code == 200
    files = response.json()["data"]
    assert any(f["file_name"] == "phx_dm_advisor.csv" for f in files)
