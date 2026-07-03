from fastapi import APIRouter

from app.graph.client import get_graph_client
from app.shared.responses import ok

router = APIRouter(prefix="/explainability", tags=["Explainability"])


def _merged(query: str, params: dict) -> dict:
    merged: dict = {}
    for entry in get_graph_client().run_query(query, params).get("results", []):
        merged.update(entry)
    return merged


@router.get("/trace/{artifact_type}/{artifact_id}")
def reasoning_trace(artifact_type: str, artifact_id: str):
    return ok(data=_merged("get_reasoning_trace", {"artifact_type": artifact_type.upper(), "artifact_id": artifact_id}))


@router.get("/recommendation/{recommendation_id}")
def recommendation_chain(recommendation_id: str):
    return ok(data=_merged("get_recommendation_detail", {"recommendation_id": recommendation_id}))


@router.get("/memory-timeline/{subject_type}/{subject_id}")
def memory_timeline(subject_type: str, subject_id: str):
    return ok(data=_merged("get_memory_timeline", {"subject_type": subject_type.upper(), "subject_id": subject_id}))
