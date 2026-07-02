from fastapi.testclient import TestClient
from app.api.main import app

def test_agentic_ai_agents_api():
    response=TestClient(app).get('/agentic-ai/agents')
    assert response.status_code == 200
    assert response.json()['success'] is True
