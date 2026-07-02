from fastapi.testclient import TestClient
from app.api.main import app

def test_knowledge_documents_api():
    client = TestClient(app)
    response = client.get("/knowledge/documents")
    assert response.status_code == 200
    assert response.json()["success"] is True
