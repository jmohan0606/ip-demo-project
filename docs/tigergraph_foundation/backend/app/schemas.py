from pydantic import BaseModel, Field

class StartRunRequest(BaseModel):
    files: list[str] | None = None
    skip_unchanged: bool = True
    batch_size: int | None = Field(default=None, ge=1, le=5000)
    mode: str = 'LOAD'

class ValidationRequest(BaseModel):
    files: list[str] | None = None

class RunActionResponse(BaseModel):
    run_id: str
    status: str
    message: str
