from fastapi.testclient import TestClient
from app.api.main import app

def test_config_summary_endpoint():
    r=TestClient(app).get('/config/summary'); assert r.status_code == 200; assert r.json()['data']['graph_name'] == 'iperform_insights_coaching_demo'
def test_adapter_endpoint():
    r=TestClient(app).get('/adapters/model'); assert r.status_code == 200; assert r.json()['success'] is True
def test_manifest_endpoint():
    r=TestClient(app).get('/manifest'); assert r.status_code == 200; assert r.json()['data']['schema_prefix'] == 'phx_dm_'
