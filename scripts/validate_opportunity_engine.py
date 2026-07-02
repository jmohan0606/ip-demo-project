from __future__ import annotations

from app.models.opportunities import OpportunityRunRequest, OpportunitySearchRequest
from app.services.opportunity_service import OpportunityService


def main() -> None:
    service = OpportunityService()
    result = service.run_opportunities(OpportunityRunRequest(write_to_tigergraph=False, limit=200))
    assert result.opportunities_created > 0
    rows = service.list_opportunities(OpportunitySearchRequest(limit=20))
    assert len(rows) > 0
    counts = service.counts()
    assert len(counts) > 0
    print("Opportunity Engine validation passed.")
    print(result.model_dump())


if __name__ == "__main__":
    main()
