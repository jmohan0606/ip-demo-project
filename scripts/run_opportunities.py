from __future__ import annotations

from app.models.opportunities import OpportunityRunRequest
from app.services.opportunity_service import OpportunityService


def main() -> None:
    result = OpportunityService().run_opportunities(OpportunityRunRequest(write_to_tigergraph=False))
    print("Opportunity run complete.")
    print(result.model_dump())


if __name__ == "__main__":
    main()
