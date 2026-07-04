from __future__ import annotations

from app.llm.client import get_llm_client
from app.models.insights_coaching import (
    CoachingPlan, CoachingTone, InsightCard, InsightCardType, InsightDashboardPayload,
    InsightEvidence, InsightRequest, InsightScopeType
)
from app.shared.ids import timestamp_id


class InsightGenerationEngine:
    def __init__(self) -> None:
        # Section-2 LLMClient adapter (mock | claude | real) — replaces the old
        # ModelAdapterFactory path that silently fell back to MockModelAdapter.
        self.llm = get_llm_client()

    def _llm_text(self, prompt: str, context: dict) -> str:
        try:
            return self.llm.generate(prompt, context)
        except Exception as exc:  # visible degradation, never a silent mock swap
            return f"(LLM unavailable: {exc})"

    def generate_payload(self, request: InsightRequest, data: dict) -> InsightDashboardPayload:
        cards = self._deterministic_cards(request, data)

        ai_summary = self._llm_text(
            f"Summarize the coaching insights for {request.scope_type.value} {request.scope_id} "
            "in 2-3 sentences, citing the concrete figures provided.",
            {
                "system_prompt": (
                    "You are the iPerform insights engine for a wealth-management firm. Return a "
                    "concise executive summary grounded ONLY in the insight cards provided — cite "
                    "their figures, never invent data."
                ),
                "insight_cards": " | ".join(
                    f"[{c.severity}] {c.title}: {c.summary}" for c in cards
                ),
            },
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

    @staticmethod
    def _opp_severity(severity: str | None) -> str:
        return {"CRITICAL": "High", "URGENT": "High", "ATTENTION": "Medium"}.get(
            (severity or "").upper(), "Low")

    def _deterministic_cards(self, request: InsightRequest, data: dict) -> list[InsightCard]:
        payload = data.get("advisor_features") or {}
        features = payload.get("features", {})
        snapshot_id = payload.get("feature_snapshot_id", "no snapshot")
        predictions = data.get("predictions") or []
        opportunities = data.get("opportunities") or []
        recommendations = data.get("recommendations") or []

        revenue = float(features.get("revenue_ltm", 0) or 0)
        growth_pct = float(features.get("revenue_growth_3m_pct", 0) or 0)
        managed_pct = round(float(features.get("managed_revenue_ratio", 0) or 0) * 100, 2)
        nnm = float(features.get("nnm_3m", 0) or 0)
        ncf = float(features.get("ncf_3m", 0) or 0)
        overdue = int(features.get("overdue_followup_count", 0) or 0)
        kpi_on_track = float(features.get("kpi_on_track_ratio", 0) or 0)

        cards: list[InsightCard] = []

        cards.append(InsightCard(
            insight_id=timestamp_id("ins"),
            card_type=InsightCardType.REVENUE,
            title="Revenue and NNM Performance Summary",
            summary=(f"LTM revenue is {round(revenue,2)} with 3-month growth of {round(growth_pct,2)}%; "
                     f"managed revenue mix is {round(managed_pct,2)}%, 3-month NNM is {round(nnm,2)} "
                     f"and NCF is {round(ncf,2)}."),
            severity="High" if nnm < 0 or ncf < 0 else "Medium",
            confidence=0.86,
            evidence=[
                InsightEvidence(source="Feature Engineering", title="Revenue LTM", detail=f"Phase-5 snapshot {snapshot_id}", value=round(revenue,2)),
                InsightEvidence(source="Feature Engineering", title="Revenue Growth 3M %", detail="Two 3-month GQ-004 windows", value=round(growth_pct,2)),
                InsightEvidence(source="Feature Engineering", title="Managed Revenue %", detail="GQ-006 managed share of product mix", value=round(managed_pct,2)),
                InsightEvidence(source="Feature Engineering", title="NNM 3M", detail="Net new money signal", value=round(nnm,2)),
            ],
            reasoning_steps=[
                f"Computed advisor feature snapshot {snapshot_id} via the Phase-5 pipeline.",
                "Compared revenue level/growth, managed mix, NNM and NCF signals.",
                "Flagged higher severity when NNM or NCF is negative.",
            ],
            recommended_actions=[
                "Review households with negative NCF or lower engagement.",
                "Prioritize managed account review where suitable and documented.",
            ],
        ))

        agp_preds = [p for p in predictions if p.get("prediction_type") == "AGP_OFF_TRACK_RISK"]
        agp_pred = agp_preds[0] if agp_preds else None
        agp_score = float(agp_pred["score"]) if agp_pred else 0.0
        cards.append(InsightCard(
            insight_id=timestamp_id("ins"),
            card_type=InsightCardType.AGP,
            title="AGP Goal and Coaching Status",
            summary=(f"AGP off-track risk score is {round(agp_score,1)}/100. {overdue} overdue follow-up(s) "
                     f"and a KPI on-track ratio of {round(kpi_on_track,3)} are the leading indicators."),
            severity="High" if agp_score >= 70 else "Medium" if agp_score >= 40 else "Low",
            confidence=float(agp_pred.get("confidence", 0.82)) if agp_pred else 0.82,
            evidence=[
                InsightEvidence(source="Prediction Engine", title="AGP_OFF_TRACK_RISK", detail=(agp_pred or {}).get("explanation", "No AGP prediction (advisor may not be enrolled)"), value=round(agp_score,1)),
                InsightEvidence(source="Feature Engineering", title="Overdue Follow-ups", detail="CRM execution feature", value=overdue),
                InsightEvidence(source="Feature Engineering", title="KPI On-Track Ratio", detail="AGP KPI measurements on/off track", value=round(kpi_on_track,3)),
            ],
            reasoning_steps=[
                "Retrieved the Phase-7 AGP off-track risk prediction with contributions.",
                "Reviewed overdue follow-ups and KPI on-track ratio as leading indicators.",
                "Mapped the 0-100 risk score into coaching severity (>=70 High, >=40 Medium).",
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
            summary=(top_opp.get("impact_summary") or f"Top opportunity is {top_opp['category']} scoring {round(float(top_opp['score']),1)}." if top_opp else "No opportunity has been generated yet."),
            severity=self._opp_severity(top_opp.get("severity")) if top_opp else "Low",
            confidence=0.84 if top_opp else 0.50,
            evidence=[
                InsightEvidence(source="Opportunity Engine", title=(top_opp.get("category", "Top Opportunity") if top_opp else "No opportunity"), detail=(f"{top_opp['opportunity_id']} severity {top_opp.get('severity')}, est. impact ${float(top_opp.get('estimated_revenue_impact') or 0):,.2f}" if top_opp else "Run opportunity detection"), value=top_opp.get("score") if top_opp else None)
            ],
            reasoning_steps=[
                "Retrieved Phase-8 severity-composed AI opportunities.",
                "Selected the highest scoring open opportunity.",
                "Prepared coaching action based on opportunity category.",
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
            severity="High" if top_rec and float(top_rec.get("priority_score", 0)) >= 70 else "Medium",
            confidence=float(top_rec.get("confidence", .65)) if top_rec else 0.50,
            evidence=[
                InsightEvidence(source="Recommendation Engine", title=(top_rec.get("title", "Recommendation") if top_rec else "No recommendation"), detail=(f"{top_rec['recommendation_id']} addresses {top_rec.get('opportunity_id')}" if top_rec else "Run recommendation engine"), value=top_rec.get("priority_score") if top_rec else None)
            ],
            reasoning_steps=([
                f"Ranked by adjusted priority {top_rec['priority_score']} = base {top_rec.get('base_priority_score')} x learned weight {top_rec.get('learning_weight')}.",
            ] if top_rec else ["Generate recommendations to enable this insight."]),
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

        summary = self._llm_text(
            f"Write a 2-sentence coaching message for {request.scope_type.value} {request.scope_id} "
            f"in a {tone.value} tone, grounded in the focus areas and actions provided.",
            {
                "system_prompt": (
                    "You are the iPerform coaching engine for a wealth-management firm. Write a "
                    "specific, encouraging coaching message using ONLY the focus areas and actions "
                    "provided; be compliance-aware and do not invent figures."
                ),
                "focus_areas": "; ".join(focus[:5]),
                "next_best_actions": "; ".join(actions[:8]),
            },
        ) if request.include_ai_generation else f"Coaching plan generated for {request.scope_type.value} {request.scope_id}."

        return CoachingPlan(
            coaching_plan_id=timestamp_id("coachplan"),
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            persona=request.persona,
            tone=tone,
            summary=summary,
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
