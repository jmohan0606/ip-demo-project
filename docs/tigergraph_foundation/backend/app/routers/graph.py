from fastapi import APIRouter, HTTPException, Query
from ..services.graph_validation_service import GraphValidationService
from ..services.tigergraph_client import TigerGraphClient

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])
tg = TigerGraphClient()
validator = GraphValidationService()

@router.get("/query/{query_name}")
def query(query_name: str, params_json: str | None = Query(default=None)):
    import json
    try:
        params = json.loads(params_json) if params_json else {}
        return tg.run_query(query_name, params)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc

@router.post("/validate/cardinality")
def cardinality(run_id: str | None = None):
    try:
        return validator.cardinality(run_id)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc

@router.post("/validate/queries")
def query_smoke():
    try:
        return validator.query_smoke()
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc

@router.get("/health-summary")
def health_summary():
    return tg.run_query("get_data_health_summary", {})
