from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.graph.tigergraph_production_runtime import get_tigergraph_production_runtime
from app.shared.responses import ok

router = APIRouter(prefix="/tigergraph-activation", tags=["TigerGraph Activation"])


class LogicalQueryRequest(BaseModel):
    logical_name: str = "advisor_context"
    params: dict = Field(default_factory=lambda: {"advisor_id": "ADV0001"})


@router.get("/status")
def status():
    return ok(data=get_tigergraph_production_runtime().status())


@router.post("/query")
def query(request: LogicalQueryRequest):
    return ok(data=get_tigergraph_production_runtime().run_logical_query(request.logical_name, request.params))


@router.post("/smoke-test")
def smoke_test():
    return ok(data=get_tigergraph_production_runtime().activate_smoke_test())
