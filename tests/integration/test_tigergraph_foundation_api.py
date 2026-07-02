from fastapi.testclient import TestClient

from app.api.main import app


def test_tigergraph_foundation_inventory_api():
    client = TestClient(app)
    response = client.get("/tigergraph-foundation/inventory")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["graph_name"] == "iperform_insights_coaching_demo"


def test_tigergraph_prefix_api():
    client = TestClient(app)
    response = client.get("/tigergraph-foundation/validate-prefix")
    assert response.status_code == 200
    assert response.json()["data"]["valid"] is True
