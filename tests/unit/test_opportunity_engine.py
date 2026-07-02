from app.models.opportunities import OpportunityRunRequest
from app.services.opportunity_service import OpportunityService


def test_opportunity_run():
    result = OpportunityService().run_opportunities(OpportunityRunRequest(write_to_tigergraph=False, limit=50))
    assert result.opportunities_created > 0
