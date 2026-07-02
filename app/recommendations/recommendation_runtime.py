from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.config import get_runtime_config
from app.graph import get_graph_runtime
from app.knowledge import get_knowledge_runtime
from app.recommendations.compliance import ComplianceService
from app.recommendations.learning_engine import LearningEngine
from app.recommendations.learning_store import LearningStore
from app.recommendations.opportunity_engine import OpportunityEngine
from app.recommendations.recommendation_engine import RecommendationEngine


class RecommendationRuntime:
    def __init__(self) -> None:
        self.config = get_runtime_config()
        self.opportunities = OpportunityEngine()
        self.recommendations = RecommendationEngine()
        self.compliance = ComplianceService()
        self.learning = LearningEngine()
        self.learning_store = LearningStore(self.config.sqlite_db_path)
        self.graph = get_graph_runtime()
        self.knowledge = get_knowledge_runtime()

    def status(self) -> dict[str, Any]:
        return {
            "runtime": "recommendation_learning_engine",
            "learning_store": self.learning_store.count(),
            "graph_runtime": self.graph.status(),
        }

    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        opportunities = self.opportunities.generate(context)
        recommendations = self.recommendations.generate(opportunities)

        enriched = []
        for rec in recommendations:
            rec_dict = asdict(rec)
            compliance = self.compliance.validate(rec_dict)
            rec_dict["compliance_status"] = compliance["status"]
            rec_dict["compliance_rules"] = compliance["rules"]

            state = self.learning_store.get_state(rec.recommendation_id)
            if state:
                rec_dict["learning_state"] = state
                rec_dict["confidence"] = max(0.0, min(1.0, rec_dict["confidence"] + state["score_adjustment"]))

            # Retrieve knowledge evidence for each rec.
            evidence = self.knowledge.search(rec.title, top_k=2).to_dict()
            rec_dict["knowledge_evidence"] = evidence.get("data", {}).get("results", [])

            # Persist recommendation metadata to graph runtime.
            self.graph.upsert_vertex("Recommendation", rec.recommendation_id, {
                "recommendation_id": rec.recommendation_id,
                "title": rec.title,
                "priority": rec.priority,
                "confidence": rec_dict["confidence"],
                "impact": rec.impact,
                "compliance_status": rec_dict["compliance_status"],
            })
            self.graph.upsert_edge("GENERATED_FROM", "Recommendation", rec.recommendation_id, "Opportunity", rec.opportunity_id, {})

            enriched.append(rec_dict)

        for opp in opportunities:
            self.graph.upsert_vertex("Opportunity", opp.opportunity_id, asdict(opp))

        return {
            "context": context,
            "opportunities": [asdict(opp) for opp in opportunities],
            "recommendations": enriched,
            "agent_trace": {
                "workflow": "recommendation_learning",
                "agents": [
                    {"agent_name": "OpportunityAgent", "status": "completed"},
                    {"agent_name": "RecommendationAgent", "status": "completed"},
                    {"agent_name": "ComplianceAgent", "status": "completed"},
                    {"agent_name": "KnowledgeAgent", "status": "completed"},
                    {"agent_name": "MemoryLearningAgent", "status": "completed"},
                ],
            },
        }

    def feedback(self, recommendation_id: str, action: str, notes: str = "") -> dict[str, Any]:
        feedback = self.learning.create_feedback(recommendation_id, action, notes)
        feedback_dict = asdict(feedback)
        self.learning_store.save_feedback(feedback_dict)

        graph_result = self.graph.persist_recommendation_feedback(feedback_dict).to_dict()
        memory_result = self.graph.persist_memory_event({
            "memory_id": f"MEM-{feedback.feedback_id}",
            "memory_type": "FeedbackLearning",
            "recommendation_id": recommendation_id,
            "action": action,
            "learning_signal": feedback.learning_signal,
            "memory_update": feedback.memory_update,
        }).to_dict()

        return {
            "feedback": feedback_dict,
            "graph_persistence": graph_result,
            "memory_persistence": memory_result,
            "ui_color": "green" if action in {"accept", "complete"} else "red" if action == "reject" else "amber" if action == "ignore" else "blue",
        }


_recommendation_runtime: RecommendationRuntime | None = None


def get_recommendation_runtime() -> RecommendationRuntime:
    global _recommendation_runtime
    if _recommendation_runtime is None:
        _recommendation_runtime = RecommendationRuntime()
    return _recommendation_runtime
