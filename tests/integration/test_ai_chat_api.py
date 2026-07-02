from fastapi.testclient import TestClient
from app.api.main import app


def test_ai_chat_history_api():
    client = TestClient(app)
    response = client.get("/ai-chat/history")
    assert response.status_code == 200
    assert response.json()["success"] is True
