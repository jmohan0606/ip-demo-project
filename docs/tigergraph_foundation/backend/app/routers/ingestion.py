from fastapi import APIRouter, HTTPException
from ..schemas import StartRunRequest, ValidationRequest, RunActionResponse
from ..services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])
service = IngestionService()

@router.post("/validate")
def validate(req: ValidationRequest):
    try:
        files = service.validate(req.files)
        return {"valid": all(x["valid"] for x in files), "files": files}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@router.post("/runs", response_model=RunActionResponse)
def start(req: StartRunRequest):
    try:
        run_id = service.start(req.files, req.skip_unchanged, req.batch_size, req.mode)
        return RunActionResponse(run_id=run_id, status="QUEUED", message="Ingestion run queued")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@router.get("/runs")
def list_runs(limit: int = 50):
    return {"runs": service.list_runs(min(max(limit, 1), 200))}

@router.get("/runs/{run_id}")
def status(run_id: str):
    value = service.status(run_id)
    if not value:
        raise HTTPException(404, "Run not found")
    return value

@router.post("/runs/{run_id}/pause")
def pause(run_id: str):
    service.pause(run_id)
    return {"run_id": run_id, "status": "PAUSED"}

@router.post("/runs/{run_id}/resume")
def resume(run_id: str):
    if not service.resume(run_id):
        raise HTTPException(409, "Run is not paused or does not exist")
    return {"run_id": run_id, "status": "RUNNING"}

@router.post("/runs/{run_id}/retry-failed", response_model=RunActionResponse)
def retry_failed(run_id: str):
    try:
        retry_run_id = service.retry_failed(run_id)
        return RunActionResponse(run_id=retry_run_id, status="RUNNING", message=f"Retry created from {run_id}")
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
