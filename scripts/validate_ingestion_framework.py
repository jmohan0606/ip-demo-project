from __future__ import annotations

from app.ingestion.entity_registry import list_entity_configs
from app.ingestion.ingestion_service import IngestionService
from app.models.ingestion import IngestionRunRequest


def main() -> None:
    configs = list_entity_configs()
    assert len(configs) >= 10

    service = IngestionService()
    result = service.run_entity_ingestion(
        IngestionRunRequest(entity_name="advisor", dry_run=True, resume=False, batch_size=25)
    )
    assert result.batch_status.total_records > 0
    assert result.batch_status.processed_records == 25

    print("Ingestion framework validation passed.")
    print(f"Entities configured: {len(configs)}")
    print(f"Advisor progress: {result.batch_status.progress_percent}%")


if __name__ == "__main__":
    main()
