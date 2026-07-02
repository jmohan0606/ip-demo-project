from fastapi import APIRouter
from ..services.tigergraph_client import TigerGraphClient
router=APIRouter(prefix="/api/v1/health",tags=["health"])
@router.get("")
def health():
    tg=TigerGraphClient().health()
    return {"status":"ok" if tg.get("healthy") else "degraded","tigergraph":tg}
