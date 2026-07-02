from app.ingestion.checkpoint_repository import CheckpointRepository
from app.ingestion.delta_detector import DeltaDetector
from app.models.ingestion import DeltaAction


def test_delta_detector_create_then_skip():
    repo = CheckpointRepository()
    detector = DeltaDetector(repo)
    record = {"advisor_id": "UNIT_ADV", "advisor_name": "Unit Test"}
    action, row_hash = detector.detect("unit_advisor", "UNIT_ADV", record)
    assert action in {DeltaAction.CREATE, DeltaAction.UPDATE}
    repo.upsert_hash("unit_advisor", "UNIT_ADV", row_hash)
    action2, _ = detector.detect("unit_advisor", "UNIT_ADV", record)
    assert action2 == DeltaAction.SKIP
