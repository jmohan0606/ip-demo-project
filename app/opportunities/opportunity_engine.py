from __future__ import annotations

from app.feature_store.feature_store_repository import FeatureStoreRepository
from app.models.opportunities import OpportunityPriority, OpportunityRecord, OpportunityType
from app.shared.ids import timestamp_id


class OpportunityEngine:
    def __init__(self) -> None:
        self.feature_repo = FeatureStoreRepository()

    def _priority(self, score: float) -> OpportunityPriority:
        if score >= 0.75:
            return OpportunityPriority.HIGH
        if score >= 0.55:
            return OpportunityPriority.MEDIUM
        return OpportunityPriority.LOW

    def _advisor_features(self) -> dict[str, dict]:
        rows = self.feature_repo.list_vectors("advisor_growth_features", limit=10000)
        return {r["entity_id"]: r["features"] for r in rows}

    def _crm_features(self) -> dict[str, dict]:
        rows = self.feature_repo.list_vectors("crm_activity_features", limit=10000)
        return {r["entity_id"]: r["features"] for r in rows}

    def _agp_features(self) -> dict[str, dict]:
        rows = self.feature_repo.list_vectors("agp_progress_features", limit=10000)
        return {r["entity_id"]: r["features"] for r in rows}

    def detect(self, entity_id: str | None = None, min_score: float = 0.45, limit: int = 500) -> list[OpportunityRecord]:
        advisor_features = self._advisor_features()
        crm_features = self._crm_features()
        agp_features = self._agp_features()

        opportunities: list[OpportunityRecord] = []
        advisor_ids = [entity_id] if entity_id else sorted(advisor_features.keys())

        for advisor_id in advisor_ids:
            f = advisor_features.get(advisor_id, {})
            crm = crm_features.get(advisor_id, {})
            agp = agp_features.get(advisor_id, {})
            merged = {**f, **crm, **agp}

            revenue = float(f.get("revenue_ltm", 0) or 0)
            managed_pct = float(f.get("managed_revenue_pct", 0) or 0)
            nnm = float(f.get("nnm_ltm", 0) or 0)
            ncf = float(f.get("ncf_ltm", 0) or 0)
            crm_count = float(crm.get("crm_activity_count", 0) or 0)
            meeting_count = float(crm.get("meeting_count", 0) or 0)
            off_track = float(agp.get("off_track_kpi_count", 0) or 0)
            avg_attainment = float(agp.get("avg_goal_attainment_pct", 0) or 0)

            candidates = []

            # Managed account expansion: strong when revenue exists but managed pct is lower.
            score = max(0, min(1, (1 - min(managed_pct, 100) / 100) * 0.55 + min(revenue / 5000000, 1) * 0.25 + min(crm_count / 80, 1) * 0.20))
            candidates.append((OpportunityType.MANAGED_ACCOUNT_EXPANSION, score, [
                f"Managed revenue percentage is {round(managed_pct, 2)}%.",
                f"Revenue signal is {round(revenue, 2)}.",
                f"CRM activity count is {int(crm_count)}."
            ]))

            # NNM growth: strong when NNM is lower/negative but CRM is present.
            nnm_gap = 1 if nnm < 0 else max(0, 1 - min(nnm / 2000000, 1))
            score = max(0, min(1, nnm_gap * 0.60 + min(crm_count / 90, 1) * 0.20 + min(revenue / 3000000, 1) * 0.20))
            candidates.append((OpportunityType.NNM_GROWTH, score, [
                f"NNM signal is {round(nnm, 2)}.",
                f"CRM activity supports follow-up motion.",
                "Opportunity can target households with liquidity or rollover potential."
            ]))

            # AUM retention: negative NCF and low meetings.
            meeting_gap = max(0, 1 - min(meeting_count / 20, 1))
            ncf_risk = 1 if ncf < 0 else 0.25
            score = max(0, min(1, ncf_risk * 0.55 + meeting_gap * 0.30 + min(revenue / 4000000, 1) * 0.15))
            candidates.append((OpportunityType.AUM_RETENTION, score, [
                f"NCF signal is {round(ncf, 2)}.",
                f"Meeting count is {int(meeting_count)}.",
                "Retention review recommended for at-risk households."
            ]))

            # AGP goal recovery.
            if agp:
                score = max(0, min(1, min(off_track / 3, 1) * 0.55 + max(0, (100 - avg_attainment) / 100) * 0.45))
                candidates.append((OpportunityType.AGP_GOAL_RECOVERY, score, [
                    f"Off-track KPI count is {int(off_track)}.",
                    f"Average goal attainment is {round(avg_attainment, 2)}%.",
                    "Manager coaching action is recommended."
                ]))

            # CRM engagement gap.
            score = max(0, min(1, max(0, 1 - min(crm_count / 60, 1)) * 0.70 + min(revenue / 3000000, 1) * 0.30))
            candidates.append((OpportunityType.CRM_ENGAGEMENT_GAP, score, [
                f"CRM activity count is {int(crm_count)}.",
                "Low engagement can reduce conversion and retention outcomes.",
                "Prompt advisor follow-up and meeting cadence review."
            ]))

            for otype, score, evidence in candidates:
                if score < min_score:
                    continue
                opportunities.append(OpportunityRecord(
                    opportunity_id=timestamp_id("opp"),
                    entity_id=advisor_id,
                    opportunity_type=otype,
                    title=f"{otype.value} for {advisor_id}",
                    description=f"Detected {otype.value.lower()} using feature store, CRM, AGP and revenue signals.",
                    score=round(score, 6),
                    priority=self._priority(score),
                    evidence=evidence,
                    reasoning_steps=[
                        "Retrieve advisor feature vector.",
                        "Evaluate revenue, NNM, NCF, CRM and AGP leading indicators.",
                        "Apply opportunity scoring rule.",
                        "Rank by score and assign priority."
                    ],
                    feature_snapshot=merged,
                ))

            if len(opportunities) >= limit:
                break

        opportunities.sort(key=lambda x: x.score, reverse=True)
        return opportunities[:limit]
