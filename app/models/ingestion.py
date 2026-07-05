from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class IngestionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class DeltaAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"
    FAILED = "failed"


class IngestionEntityConfig(BaseModel):
    entity_name: str
    csv_file_name: str
    primary_key: str
    tigergraph_vertex: str
    required_columns: list[str]
    edge_files: list[str] = Field(default_factory=list)
    batch_size: int = 500


class IngestionBatchStatus(BaseModel):
    batch_id: str
    entity_name: str
    file_name: str
    status: IngestionStatus
    total_records: int = 0
    processed_records: int = 0
    created_records: int = 0
    updated_records: int = 0
    skipped_records: int = 0
    failed_records: int = 0
    last_processed_row: int = 0
    progress_percent: float = 0.0
    message: str | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IngestionRecordResult(BaseModel):
    row_number: int
    entity_name: str
    primary_key: str
    action: DeltaAction
    success: bool
    message: str | None = None


class IngestionRunRequest(BaseModel):
    entity_name: str
    file_name: str | None = None
    resume: bool = True
    dry_run: bool = False
    batch_size: int | None = None


class IngestionRunResponse(BaseModel):
    batch_status: IngestionBatchStatus
    records: list[IngestionRecordResult] = Field(default_factory=list)
