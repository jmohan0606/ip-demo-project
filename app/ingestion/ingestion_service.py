from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from app.config.settings import get_settings
from app.ingestion.checkpoint_repository import CheckpointRepository
from app.ingestion.delta_detector import DeltaDetector
from app.ingestion.entity_registry import get_entity_config, list_entity_configs
from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient
from app.ingestion.validation_engine import ValidationEngine
from app.models.ingestion import (
    DeltaAction,
    IngestionBatchStatus,
    IngestionRecordResult,
    IngestionRunRequest,
    IngestionRunResponse,
    IngestionStatus,
)
from app.shared.ids import timestamp_id


class IngestionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.checkpoints = CheckpointRepository()
        self.validator = ValidationEngine()
        self.delta = DeltaDetector(self.checkpoints)
        self.upsert = TigerGraphUpsertClient()
        self.sample_data_dir = Path("tigergraph/sample_data")

    def list_entities(self) -> list[dict]:
        return [config.model_dump() for config in list_entity_configs()]

    def list_batches(self) -> list[dict]:
        return self.checkpoints.list_batches()

    def _count_records(self, file_path: Path) -> int:
        with file_path.open(encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)

    def run_entity_ingestion(self, request: IngestionRunRequest) -> IngestionRunResponse:
        config = get_entity_config(request.entity_name)
        file_name = request.file_name or config.csv_file_name
        file_path = self.sample_data_dir / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        total_records = self._count_records(file_path)
        previous = self.checkpoints.latest_batch(config.entity_name, file_name) if request.resume else None

        should_resume = (
            request.resume
            and previous is not None
            and previous.status in {IngestionStatus.FAILED, IngestionStatus.PAUSED, IngestionStatus.RUNNING}
        )
        start_row = previous.last_processed_row + 1 if should_resume else 1

        status = IngestionBatchStatus(
            batch_id=previous.batch_id if should_resume else timestamp_id("batch"),
            entity_name=config.entity_name,
            file_name=file_name,
            status=IngestionStatus.RUNNING,
            total_records=total_records,
            processed_records=previous.processed_records if should_resume else 0,
            created_records=previous.created_records if should_resume else 0,
            updated_records=previous.updated_records if should_resume else 0,
            skipped_records=previous.skipped_records if should_resume else 0,
            failed_records=previous.failed_records if should_resume else 0,
            last_processed_row=previous.last_processed_row if should_resume else 0,
            progress_percent=previous.progress_percent if should_resume else 0,
            message="Running",
        )
        self.checkpoints.save_batch(status)

        results: list[IngestionRecordResult] = []
        batch_size = request.batch_size or config.batch_size

        with file_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            header_errors = self.validator.validate_header(config, reader.fieldnames or [])
            if header_errors:
                status.status = IngestionStatus.FAILED
                status.message = "; ".join(header_errors)
                self.checkpoints.save_batch(status)
                return IngestionRunResponse(batch_status=status, records=[])

            for row_number, record in enumerate(reader, start=1):
                if row_number < start_row:
                    continue

                primary_key = record.get(config.primary_key, "")
                try:
                    validation_errors = self.validator.validate_record(config, record)
                    if validation_errors:
                        raise ValueError("; ".join(validation_errors))

                    action, row_hash = self.delta.detect(config.entity_name, primary_key, record)

                    if action == DeltaAction.SKIP:
                        status.skipped_records += 1
                        success = True
                        message = "Unchanged"
                    else:
                        if not request.dry_run:
                            self.upsert.upsert_vertex(config.tigergraph_vertex, primary_key, record)
                            self.checkpoints.upsert_hash(config.entity_name, primary_key, row_hash)

                        if action == DeltaAction.CREATE:
                            status.created_records += 1
                        else:
                            status.updated_records += 1

                        success = True
                        message = action.value

                    status.processed_records += 1
                    status.last_processed_row = row_number
                    status.progress_percent = round((status.last_processed_row / total_records) * 100, 2) if total_records else 100
                    status.updated_at = datetime.utcnow()
                    self.checkpoints.save_batch(status)

                    results.append(
                        IngestionRecordResult(
                            row_number=row_number,
                            entity_name=config.entity_name,
                            primary_key=primary_key,
                            action=action,
                            success=success,
                            message=message,
                        )
                    )

                except Exception as exc:
                    status.failed_records += 1
                    status.processed_records += 1
                    status.last_processed_row = row_number
                    status.progress_percent = round((status.last_processed_row / total_records) * 100, 2) if total_records else 100
                    status.status = IngestionStatus.FAILED
                    status.message = f"Failed at row {row_number}: {exc}"
                    status.updated_at = datetime.utcnow()
                    self.checkpoints.save_batch(status)
                    self.checkpoints.save_error(
                        error_id=timestamp_id("err"),
                        batch_id=status.batch_id,
                        entity_name=config.entity_name,
                        row_number=row_number,
                        primary_key=primary_key,
                        error_message=str(exc),
                        raw_record=record,
                    )
                    results.append(
                        IngestionRecordResult(
                            row_number=row_number,
                            entity_name=config.entity_name,
                            primary_key=primary_key,
                            action=DeltaAction.FAILED,
                            success=False,
                            message=str(exc),
                        )
                    )
                    return IngestionRunResponse(batch_status=status, records=results[-batch_size:])

                if len(results) >= batch_size:
                    # Return after one batch so UI can show progress and call repeatedly.
                    status.message = "Batch completed; call again to continue if needed."
                    self.checkpoints.save_batch(status)
                    return IngestionRunResponse(batch_status=status, records=results[-batch_size:])

        status.status = IngestionStatus.COMPLETED
        status.progress_percent = 100.0
        status.message = "Completed"
        status.updated_at = datetime.utcnow()
        self.checkpoints.save_batch(status)
        return IngestionRunResponse(batch_status=status, records=results[-batch_size:])
