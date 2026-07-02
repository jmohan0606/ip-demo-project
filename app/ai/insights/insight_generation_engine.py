from __future__ import annotations

from app.ai.adapters.adapter_factory import ModelAdapterFactory
from app.models.enums import AdapterProvider
from app.models.insights_coaching import (
    CoachingPlan, CoachingTone, InsightCard, InsightCardType, InsightDashboardPayload,
    InsightEvidence, InsightRequest, InsightScopeType
)
from app.shared.ids import timestamp_id


class InsightGenerationEngine:
    def __init__(self) -> None:
        self.adapter = ModelAdapterFactory.create(AdapterProvider.OPENAI)

    def generate_payload(self, request: InsightRequest, data: dict) -> InsightDashboardPayload:
        cards = self._deterministic_cards(request, data)

        # Use adapter lightly for summary. Mock adapter will return deterministic fallback.
        ai_summary = self.adapter.generate_text(
            prompt=f"Summarize coaching insights for {request.scope_type.value} {request.scope_id} using {len(cards)} insight cards.",
            system_prompt="Return a concise executive summary.",
        ) if request.include_ai_generation else ""

        executive_summary = self._executive_summary(request, cards, ai_summary)
        coaching_plan = self._coaching_plan(request, cards)

        return InsightDashboardPayload(
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            persona=request.persona,
            time_period=request.time_period,
            executive_summary=executive_summary,
            cards=cards,
            coaching_plan=coaching_plan,
            context_summary=(data.get("context_package") or {}).get("context_summary"),
        )

    def _deterministic_cards(self, request: InsightRequest, data: dict) -> list[InsightCard]:
        features = (data.get("advisor_features") or {}).get("features", {}) if data.get("advisor_features") else {}
        predictions = data.get("predictions") or []
        opportunities = data.get("opportunities") or []
        recommendations = data.get("recommendations") or []

        revenue = float(features.get("revenue_ltm", 0) or 0)
        managed_pct = float(features.get("managed_revenue_pct", 0) or 0)
        nnm = float(features.get("nnm_ltm", 0) or 0)
        ncf = float(features.get("ncf_ltm", 0) or 0)
        crm_count = float(features.get("crm_activity_count", 0) or 0)

        cards: list[InsightCard] = []

        cards.append(InsightCard(
            insight_id=timestamp_id("ins"),
            card_type=InsightCardType.REVENUE,
            title="Revenue and NNM Performance Summary",
            summary=f"Revenue signal is {round(revenue,2)}, managed revenue mix is {round(managed_pct,2)}%, NNM is {round(nnm,2)}, and NCF is {round(ncf,2)}.",
            severity="High" if nnm < 0 or ncf < 0 else "Medium",
            confidence=0.86,
            evidence=[
                InsightEvidence(source="Feature Store", title="Revenue LTM", detail="Materialized advisor growth feature", value=round(revenue,2)),
                InsightEvidence(source="Feature Store", title="Managed Revenue %", detail="Managed revenue share", value=round(managed_pct,2)),
                InsightEvidence(source="Feature Store", title="NNM LTM", detail="Net new money signal", value=round(nnm,2)),
            ],
            reasoning_steps=[
                "Retrieved advisor growth feature vector.",
                "Compared revenue, managed revenue, NNM and NCF signals.",
                "Flagged higher severity when NNM or NCF is negative.",
            ],
            recommended_actions=[
                "Review households with negative NCF or lower engagement.",
                "Prioritize managed account review where suitable and documented.",
            ],
        ))

        agp_preds = [p for p in predictions if p.get("prediction_type") == "AGP Goal Risk"]
        agp_score = float(agp_preds[0]["score"]) if agp_preds else 0
        cards.append(InsightCard(
            insight_id=timestamp_id("ins"),
            card_type=InsightCardType.AGP,
            title="AGP Goal and Coaching Status",
            summary=f"AGP risk score is {round(agp_score,3)}. CRM activity count is {int(crm_count)} and should be reviewed as a leading indicator.",
            severity="High" if agp_score >= .7 else "Medium" if agp_score >= .4 else "Low",
            confidence=0.82,
            evidence=[
                InsightEvidence(source="Prediction Engine", title="AGP Goal Risk", detail="Local sklearn risk score", value=round(agp_score,3)),
                InsightEvidence(source="Feature Store", title="CRM Activity Count", detail="CRM engagement feature", value=int(crm_count)),
            ],
            reasoning_steps=[
                "Retrieved AGP risk prediction.",
                "Reviewed CRM activity as leading indicator.",
                "Mapped risk score into coaching severity.",
            ],
            recommended_actions=[
                "MDW/DDW should review off-track AGP KPIs.",
                "Create weekly coaching actions for prospecting, meetings and follow-ups.",
            ],
        ))

        top_opp = opportunities[0] if opportunities else None
        cards.append(InsightCard(
            insight_id=timestamp_id("ins"),
            card_type=InsightCardType.OPPORTUNITY,
            title="Top Opportunity",
            summary=(f"Top opportunity is {top_opp['opportunity_type']} with score {round(float(top_opp['score']),3)}." if top_opp else "No opportunity has been generated yet."),
            severity=(top_opp.get("priority", "Medium") if top_opp else "Low"),
            confidence=0.84 if top_opp else 0.50,
            evidence=[
                InsightEvidence(source="Opportunity Engine", title="Top Opportunity", detail=top_opp.get("description", "") if top_opp else "No opportunity", value=top_opp.get("score") if top_opp else None)
            ],
            reasoning_steps=[
                "Retrieved ranked opportunities.",
                "Selected highest scoring open opportunity.",
                "Prepared coaching action based on opportunity type.",
            ],
            recommended_actions=[
                "Review top opportunity evidence before advisor action.",
                "Convert high priority opportunity into recommendation workflow.",
            ],
        ))

        top_rec = recommendations[0] if recommendations else None
        cards.append(InsightCard(
            insight_id=timestamp_id("ins"),
            card_type=InsightCardType.RECOMMENDATION,
            title="Recommended Next Best Action",
            summary=(top_rec["action_text"] if top_rec else "No recommendation has been generated yet."),
            severity="High" if top_rec and float(top_rec.get("score", 0)) > .75 else "Medium",
            confidence=float(top_rec.get("confidence", .65)) if top_rec else 0.50,
            evidence=[
                InsightEvidence(source="Recommendation Engine", title="Recommendation", detail=top_rec.get("rationale", "") if top_rec else "No recommendation", value=top_rec.get("score") if top_rec else None)
            ],
            reasoning_steps=(top_rec.get("reasoning_steps", []) if top_rec else ["Generate recommendations to enable this insight."]),
            recommended_actions=[top_rec["action_text"]] if top_rec else ["Run recommendation engine."],
        ))

        return cards

    def _executive_summary(self, request: InsightRequest, cards: list[InsightCard], ai_summary: str) -> str:
        high = sum(1 for c in cards if c.severity == "High")
        base = f"{request.scope_type.value} {request.scope_id} has {len(cards)} insight cards, including {high} high-severity items."
        if ai_summary:
            return f"{base} {ai_summary}"
        return base

    def _coaching_plan(self, request: InsightRequest, cards: list[InsightCard]) -> CoachingPlan:
        actions = []
        focus = []
        for card in cards:
            focus.append(card.title)
            actions.extend(card.recommended_actions[:2])

        tone = CoachingTone.ADVISOR if request.scope_type == InsightScopeType.ADVISOR else CoachingTone.MANAGER
        if request.persona in {"Firm", "DDW"}:
            tone = CoachingTone.EXECUTIVE

        return CoachingPlan(
            coaching_plan_id=timestamp_id("coachplan"),
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            persona=request.persona,
            tone=tone,
            summary=f"Coaching plan generated for {request.scope_type.value} {request.scope_id}.",
            focus_areas=focus[:5],
            next_best_actions=actions[:8],
            manager_review_notes=[
                "Review evidence and confidence before communicating action.",
                "Confirm suitability, risk profile and documentation requirements.",
                "Capture feedback after action is accepted, rejected or completed.",
            ],
            advisor_talk_track=[
                "Here is what changed in your metrics.",
                "Here is the evidence behind the recommendation.",
                "Here are the next actions to take this week.",
            ],
            confidence=0.84,
        )
