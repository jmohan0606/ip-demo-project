from app.models.insights_coaching import InsightRequest, InsightScopeType
from app.services.insights_coaching_service import InsightsCoachingService


def test_insight_payload_generation():
    payload = InsightsCoachingService().generate_dashboard_payload(
        InsightRequest(scope_type=InsightScopeType.ADVISOR, scope_id="ADV0001", write_to_tigergraph=False)
    )
    assert payload.cards
    assert payload.coaching_plan is not None
