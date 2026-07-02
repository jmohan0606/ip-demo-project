from __future__ import annotations

from app.models.features import FeatureMaterializationRequest
from app.models.opportunities import OpportunityRunRequest, OpportunityRunResult, OpportunitySearchRequest
from app.opportunities.opportunity_engine import OpportunityEngine
from app.opportunities.opportunity_repository import OpportunityRepository
from app.opportunities.tigergraph_opportunity_linker import TigerGraphOpportunityLinker
from app.services.feature_store_service import FeatureStoreService


class OpportunityService:
    def __init__(self) -> None:
        self.feature_service = FeatureStoreService()
        self.engine = OpportunityEngine()
        self.repo = OpportunityRepository()
        self.linker = TigerGraphOpportunityLinker()

    def run_opportunities(self, request: OpportunityRunRequest) -> OpportunityRunResult:
        # Ensure feature store is populated before scoring opportunities.
        self.feature_service.materialize(FeatureMaterializationRequest())
        opportunities = self.engine.detect(request.entity_id, request.min_score, request.limit)
        for opp in opportunities:
            self.repo.save_opportunity(opp)
            if request.write_to_tigergraph:
                self.linker.upsert_opportunity(opp)
        return OpportunityRunResult(
            opportunities_created=len(opportunities),
            status="completed",
            message=f"Generated {len(opportunities)} opportunities.",
        )

    def list_opportunities(self, request: OpportunitySearchRequest) -> list[dict]:
        return self.repo.list_opportunities(
            entity_id=request.entity_id,
            opportunity_type=request.opportunity_type.value if request.opportunity_type else None,
            priority=request.priority.value if request.priority else None,
            limit=request.limit,
        )

    def counts(self) -> list[dict]:
        return self.repo.counts()
