from __future__ import annotations

from app.coaching.service import CoachingReviewService
from app.models.ai_chat import ChatContextItem, ChatContextSource, ChatRequest
from app.models.insights_coaching import InsightRequest, InsightScopeType
from app.models.knowledge import KnowledgeSearchRequest
from app.models.memory import MemoryRetrievalRequest, MemoryScopeType
from app.opportunities.service import OpportunityDetectionService
from app.recommendations.service import RecommendationService as RecommendationPipelineService
from app.services.context_service import ContextService
from app.services.insights_coaching_service import InsightsCoachingService
from app.services.knowledge_management_service import KnowledgeManagementService
from app.prediction.prediction_repository import PredictionRepository


class ChatContextAssembler:
    def __init__(self) -> None:
        self.context_service = ContextService()
        self.knowledge_service = KnowledgeManagementService()
        self.insight_service = InsightsCoachingService()
        self.prediction_repo = PredictionRepository()
        self.opportunity_service = OpportunityDetectionService()
        self.recommendation_service = RecommendationPipelineService()
        self.coaching_service = CoachingReviewService()

    def assemble(self, request: ChatRequest) -> list[ChatContextItem]:
        items, _ = self.assemble_with_trace(request)
        return items

    def assemble_with_trace(self, request: ChatRequest) -> tuple[list[ChatContextItem], dict]:
        """Assemble broadly, then rerank by the question and keep the top-K most relevant
        (Section 11.6). Returns the pruned items + a visible pipeline trace."""
        items = self._assemble_raw(request)
        return self._rerank_and_prune(request, items)

    def _assemble_raw(self, request: ChatRequest) -> list[ChatContextItem]:
        items: list[ChatContextItem] = []

        # Section 11.6: scope-aware reasoning — rollup scopes (DDW/MDW asking about a division/
        # firm) get REAL aggregate context, not one resolved advisor's story.
        if request.scope_type.value != "Advisor":
            try:
                from app.scope.rollup import ScopeRollupService

                roll = ScopeRollupService().summary(request.scope_type.value.upper(), request.scope_id)
                t = roll.get("totals", {})
                tops = roll.get("top_advisors", [])[:3]
                bottoms = roll.get("bottom_advisors", roll.get("needs_attention", []))[:3]
                summary = (
                    f"Scope {request.scope_type.value} {request.scope_id}: {t.get('advisor_count')} advisors, "
                    f"revenue ${t.get('revenue_ltm', 0):,.0f}, AUM ${t.get('aum_total', 0):,.0f}, "
                    f"avg goal attainment {t.get('avg_goal_attainment', '?')}%. "
                    f"Top advisors: {', '.join(a.get('advisor_name', a.get('advisor_id','')) for a in tops)}. "
                    f"Needs attention: {', '.join(a.get('advisor_name', a.get('advisor_id','')) for a in bottoms)}."
                )
                items.append(ChatContextItem(
                    source=ChatContextSource.INSIGHTS, title="Scope Rollup (aggregate)",
                    content=summary, score=100.0, metadata={"rollup": roll.get("totals", {}), "scope_aware": True}))
            except Exception as exc:  # noqa: BLE001
                items.append(ChatContextItem(source=ChatContextSource.INSIGHTS,
                             title="Scope Rollup Unavailable", content=str(exc), score=0))

        if request.include_memory:
            try:
                memory_scope = MemoryScopeType.ADVISOR if request.scope_type.value == "Advisor" else MemoryScopeType(request.scope_type.value)
                package = self.context_service.build_context_package(
                    MemoryRetrievalRequest(
                        scope_type=memory_scope,
                        scope_id=request.scope_id,
                        query=request.question,
                        limit=8,
                    )
                )
                items.append(ChatContextItem(
                    source=ChatContextSource.CONTEXT_MEMORY,
                    title="Context Memory Summary",
                    content=package.context_summary,
                    score=float(package.evidence_count),
                    metadata={"evidence_count": package.evidence_count},
                ))
            except Exception as exc:
                items.append(ChatContextItem(
                    source=ChatContextSource.CONTEXT_MEMORY,
                    title="Context Memory Unavailable",
                    content=str(exc),
                    score=0,
                ))

        if request.include_knowledge:
            try:
                search = self.knowledge_service.search(
                    KnowledgeSearchRequest(query=request.question, top_k=4)
                )
                seen_chunks: set[str] = set()
                for result in search.results:
                    if result.chunk_text in seen_chunks:
                        continue  # identical chunk indexed more than once — keep one
                    seen_chunks.add(result.chunk_text)
                    items.append(ChatContextItem(
                        source=ChatContextSource.KNOWLEDGE_RAG,
                        title=result.document_name,
                        content=result.chunk_text,
                        score=result.score,
                        metadata=result.metadata,
                    ))
            except Exception as exc:
                items.append(ChatContextItem(
                    source=ChatContextSource.KNOWLEDGE_RAG,
                    title="Knowledge Search Unavailable",
                    content=str(exc),
                    score=0,
                ))

        entity_id = request.scope_id if request.scope_type.value == "Advisor" else None

        # Manager-assigned coaching tasks feed the AI as real context (CLAUDE.md 9.5):
        # instructions a manager assigns actually steer the assistant's answers.
        if entity_id:
            try:
                open_tasks = self.coaching_service.open_tasks_for_context(entity_id)
                if open_tasks:
                    lines = [f"- [{t['category']} · {t['priority']}] {t['title']}: {t['instruction']} (assigned by {t['assigned_by']})" for t in open_tasks]
                    items.append(ChatContextItem(
                        source=ChatContextSource.COACHING_TASKS,
                        title="Manager Coaching Tasks",
                        content="Open coaching tasks assigned to this advisor:\n" + "\n".join(lines),
                        score=float(len(open_tasks)),
                        metadata={"open_task_count": len(open_tasks)},
                    ))
            except Exception:
                pass

            # Section 13.4: what this advisor has recently DONE with their recommendations
            # + the recorded impact — so "what did I complete and what was the impact?" is
            # answerable from real state, not just the static feature snapshot. High score
            # keeps it prominent through the reranker for lifecycle questions.
            try:
                from app.recommendations.lifecycle import RecommendationLifecycleService
                hist = RecommendationLifecycleService().recent_activity_for_advisor(entity_id, limit=5)
                if hist["events"]:
                    lines = []
                    completed = []
                    for e in hist["events"]:
                        line = f"- {e['status']} {(e['created_ts'] or '')[:10]}: {e['title']}"
                        if e.get("note"):
                            line += f" — {e['note']}"
                        # Always surface the recorded dollar impact for a completed action
                        # (independent of the note), so the assistant can narrate the
                        # measured outcome, not just that something was done.
                        if e.get("impact_amount"):
                            line += f" [measured impact +${e['impact_amount']:,.0f}, transaction {e['source_transaction_id']}]"
                        lines.append(line)
                        if str(e.get("status", "")).upper() == "COMPLETED" and e.get("impact_amount"):
                            completed.append(e)
                    # An explicit, plain-language completion summary the LLM can echo directly.
                    summary = ""
                    if completed:
                        top = max(completed, key=lambda x: x.get("impact_amount") or 0)
                        summary = (
                            f"\nSummary: {entity_id} has completed {len(completed)} recommendation(s); "
                            f"most recent notable completion \"{top['title']}\" recorded a measured "
                            f"revenue impact of +${top['impact_amount']:,.0f}. "
                            f"Cumulative recorded impact across all completed actions: ${hist['total_impact']:,.0f}."
                        )
                    items.append(ChatContextItem(
                        source=ChatContextSource.RECOMMENDATION_LIFECYCLE,
                        title="Recommendation Actions & Recorded Impact",
                        content=(f"Recent recommendation lifecycle for {entity_id}:\n" + "\n".join(lines)
                                 + (summary or f"\nCumulative recorded impact: ${hist['total_impact']:,.0f}.")),
                        score=95.0,
                        metadata={"ledger_ids": hist["ledger_ids"], "lifecycle": True,
                                  "completed_count": len(completed)},
                    ))
            except Exception:
                pass

        # Graph relational reasoning (multi-hop traversal + prior-reasoning reuse). This is the
        # capability that distinguishes the temporal knowledge graph from a flat context bundle:
        # the answer is grounded in RELATIONSHIPS walked across the graph (advisor→households→
        # opportunities, advisor→similar advisors→their successful actions; or scope→advisors→
        # households), plus prior reasoning traces retrieved for the advisor. High score keeps it
        # prominent through the reranker.
        try:
            from app.ai.reasoning.graph_reasoner import GraphReasoner

            reasoner = GraphReasoner()
            if entity_id:  # advisor scope
                trav = reasoner.advisor_traversal(entity_id)
                priors = reasoner.prior_reasoning(entity_id, limit=3)
                content = reasoner.render_advisor_reasoning(trav, priors)
                if content:
                    items.append(ChatContextItem(
                        source=ChatContextSource.GRAPH_REASONING,
                        title="Graph Relational Reasoning (multi-hop traversal + prior reasoning)",
                        content=content, score=97.0,
                        metadata={"traversal": trav, "path": trav.get("path", []),
                                  "prior_reasoning_ids": [p["reasoning_id"] for p in priors],
                                  "reasoning": True}))
            else:  # rollup scope (division/market/region/firm)
                trav = reasoner.scope_traversal(request.scope_type.value.upper(), request.scope_id)
                content = reasoner.render_scope_reasoning(trav)
                if content:
                    items.append(ChatContextItem(
                        source=ChatContextSource.GRAPH_REASONING,
                        title=f"Graph Relational Reasoning across {request.scope_type.value} {request.scope_id}",
                        content=content, score=97.0,
                        metadata={"traversal": trav, "path": trav.get("path", []), "reasoning": True}))
        except Exception as exc:  # noqa: BLE001 — reasoning augments, never blocks the answer
            items.append(ChatContextItem(source=ChatContextSource.GRAPH_REASONING,
                                         title="Graph Relational Reasoning Unavailable", content=str(exc), score=0))

        # ---- REQ-3 full-context domains (advisor scope): AGP status, CRM pipeline,
        # household-level ML risk, GNN peer benchmark, learning state. Retrieved broadly;
        # the question-relevance reranker decides what actually reaches the prompt.
        if entity_id:
            try:  # AGP program status — real AGP-004 banded score with component explanation
                from app.agp.service import AgpService
                ts = AgpService().track_status(entity_id)
                if ts.get("enrolled"):
                    comp = ts.get("components", {})
                    items.append(ChatContextItem(
                        source=ChatContextSource.AGP_STATUS, title="AGP Track Status",
                        content=(f"AGP status for {entity_id}: {ts.get('band')} (risk score {ts.get('score')}). "
                                 f"{ts.get('explanation', '')} Components: attainment_gap {comp.get('attainment_gap')}, "
                                 f"time_pressure {comp.get('time_pressure')}, crm_execution_risk {comp.get('crm_execution_risk')}."),
                        score=70.0, metadata=ts))
                else:
                    items.append(ChatContextItem(
                        source=ChatContextSource.AGP_STATUS, title="AGP Track Status",
                        content=f"{entity_id} is NOT enrolled in the AGP growth program.",
                        score=40.0, metadata=ts))
            except Exception:
                pass

            try:  # CRM pipeline + open work — leads/referrals/opportunities by stage/status
                from app.crm.service import CrmService
                crm = CrmService()
                pipe = crm.pipeline_by_stage(entity_id).get("pipeline_by_stage", [])
                work = crm.work_summary(entity_id).get("work_summary", [])
                pipe_txt = "; ".join(
                    f"{p['stage']}: {p['opportunity_count']} opp(s) ${p['pipeline_amount']:,.0f} "
                    f"(weighted ${p['weighted_amount']:,.0f})" for p in pipe)
                work_txt = "; ".join(
                    f"{w['work_type']} {w['status']}: {w['item_count']} (${w['estimated_value']:,.0f})" for w in work)
                items.append(ChatContextItem(
                    source=ChatContextSource.CRM_PIPELINE, title="CRM Pipeline & Open Work",
                    content=f"Pipeline by stage — {pipe_txt or 'none'}. Work items — {work_txt or 'none'}.",
                    score=65.0, metadata={"pipeline": pipe, "work": work}))
            except Exception:
                pass

            try:  # Household churn/attrition propensity (ML model, honest caveat carried along)
                from app.ml.client import get_model_client
                hh = get_model_client().household_churn(entity_id)
                if hh.get("available") and hh.get("households"):
                    ranked = sorted(hh["households"], key=lambda h: -(h.get("propensity") or 0))[:6]
                    hh_txt = "; ".join(f"{h['household_id']} {h.get('band')} ({h.get('propensity')})" for h in ranked)
                    items.append(ChatContextItem(
                        source=ChatContextSource.HOUSEHOLD_RISK, title="Household Attrition Risk (ML)",
                        content=(f"Model {hh.get('model')}: per-household attrition propensity (highest first): {hh_txt}. "
                                 f"Caveat: {hh.get('caveat', '')}"),
                        score=60.0, metadata={"model": hh.get("model"), "households": ranked}))
            except Exception:
                pass

            try:  # GNN peer benchmark — WHO the similar advisors are and the metric gaps
                from app.scope.dashboard import ScopeDashboardService
                bench = ScopeDashboardService()._advisor_benchmark(entity_id)  # noqa: SLF001 — shared computation
                if bench.get("metrics"):
                    peers_txt = ", ".join(f"{p['advisor_name']} ({p['score']})" for p in bench.get("peers", []))
                    gaps = "; ".join(
                        f"{m['metric']}: you {m['you']} vs peer avg {m['peer_avg']} ({m['vs_peer_pct']:+}%)"
                        for m in bench["metrics"] if m.get("vs_peer_pct") is not None)
                    items.append(ChatContextItem(
                        source=ChatContextSource.PEER_BENCHMARK, title="GNN Peer Benchmark",
                        content=(f"Peer group by {bench.get('model')} embedding similarity: {peers_txt}. "
                                 f"Metric comparison — {gaps}."),
                        score=68.0, metadata={"model": bench.get("model"), "peers": bench.get("peers"),
                                              "metrics": bench.get("metrics")}))
            except Exception:
                pass

        try:  # Feedback-learning state — how accept/reject history has moved the ranking weights
            from app.feedback.service import FeedbackLearningService
            state = FeedbackLearningService().learning_state()
            weights = state.get("weights", [])
            if weights:
                w_txt = "; ".join(
                    f"{w['family']} {w['weight']} ({w['feedback_count']} feedback events)" for w in weights)
                items.append(ChatContextItem(
                    source=ChatContextSource.LEARNING_STATE, title="Recommendation Learning Weights",
                    content=("Current RL/bandit ranking weights learned from real accept/reject/complete feedback: "
                             + w_txt + ". Weights >1 boost that recommendation family's ranking; <1 demotes it."),
                    score=45.0, metadata={"weights": weights}))
        except Exception:
            pass

        if request.include_insights:
            try:
                payload = self.insight_service.generate_dashboard_payload(
                    InsightRequest(
                        scope_type=InsightScopeType(request.scope_type.value),
                        scope_id=request.scope_id,
                        persona=request.persona.value,
                        question=request.question,
                        write_to_tigergraph=False,
                        write_to_memory=False,
                    )
                )
                items.append(ChatContextItem(
                    source=ChatContextSource.INSIGHTS,
                    title="Generated Insight Summary",
                    content=payload.executive_summary,
                    score=len(payload.cards),
                    metadata={"card_count": len(payload.cards)},
                ))
            except Exception as exc:
                items.append(ChatContextItem(
                    source=ChatContextSource.INSIGHTS,
                    title="Insights Unavailable",
                    content=str(exc),
                    score=0,
                ))

        try:
            predictions = self.prediction_repo.list_predictions(entity_id=entity_id, limit=5)
            for p in predictions[:5]:
                items.append(ChatContextItem(
                    source=ChatContextSource.PREDICTIONS,
                    title=p.get("prediction_type", "Prediction"),
                    content=p.get("explanation", ""),
                    score=p.get("score"),
                    metadata=p,
                ))
        except Exception:
            pass

        if entity_id:
            try:
                # Real Phase-8 detection (severity-composed opportunities with lineage) — the
                # same OpportunityDetectionService the /opportunities router and agent toolbox
                # use. Replaces the legacy repo-backed OpportunityService, which read an
                # unpopulated store and returned zero opportunities for chat grounding.
                opportunities = self.opportunity_service.detect_for_advisor(entity_id)["opportunities"]
                for o in opportunities[:5]:
                    items.append(ChatContextItem(
                        source=ChatContextSource.OPPORTUNITIES,
                        title=o.get("opportunity_type") or "Opportunity",
                        content=o.get("impact_summary", ""),
                        score=o.get("score"),
                        metadata=o,
                    ))
            except Exception:
                pass

        if entity_id:
            try:
                # Real Phase-8/9 learning-weighted next-best-actions (same pipeline the
                # /recommendations router uses). Replaces the legacy repo-backed
                # list_recommendations, which read an unpopulated store and returned zero recs.
                recommendations = self.recommendation_service.generate_for_advisor(entity_id)["recommendations"]
                for r in recommendations[:5]:
                    items.append(ChatContextItem(
                        source=ChatContextSource.RECOMMENDATIONS,
                        title=r.get("title", "Recommendation"),
                        content=r.get("action_text", ""),
                        score=r.get("priority_score", r.get("score")),
                        metadata=r,
                    ))
            except Exception:
                pass

        return items

    def _rerank_and_prune(self, request: ChatRequest, items: list[ChatContextItem]) -> tuple[list[ChatContextItem], dict]:
        """Rank the assembled items by relevance to the question (RerankClient) and keep the
        top-K — 'retrieve broadly, then keep only what's relevant'. Always keeps the scope
        rollup item for rollup scopes. Returns (pruned_items, trace)."""
        from app.config.settings import get_settings
        from app.llm.rerank_client import get_rerank_client

        settings = get_settings()
        top_k = settings.context_rerank_top_k
        if not items:
            return items, {"resolved_scope": f"{request.scope_type.value}:{request.scope_id}",
                           "retrieved": [], "kept": 0, "pruned": 0, "reranker": None}

        docs = [f"{it.title}. {it.content}"[:1000] for it in items]
        reranker = get_rerank_client()
        try:
            ranked = reranker.rerank(request.question, docs)
        except Exception:  # noqa: BLE001 — never let ranking break assembly
            ranked = [{"index": i, "score": it.score or 0.0} for i, it in enumerate(items)]
        order = {r["index"]: r["score"] for r in ranked}
        # sort by rerank score; force-keep the scope-rollup item (aggregate answer basis) and the
        # graph relational-reasoning item (multi-hop traversal + prior reasoning must reach the LLM)
        def _keep_rank(i: int) -> float:
            meta = items[i].metadata or {}
            if meta.get("scope_aware"):
                return 2.0  # always top
            if meta.get("reasoning") and items[i].source == ChatContextSource.GRAPH_REASONING:
                return 1.9  # always keep graph relational reasoning
            return order.get(i, 0.0)

        idx_sorted = sorted(range(len(items)), key=lambda i: -_keep_rank(i))
        kept_idx = idx_sorted[:top_k]
        retrieved_trace = [
            {"source": items[i].source.value, "title": items[i].title,
             "rank_score": round(order.get(i, 0.0), 4), "kept": i in kept_idx}
            for i in idx_sorted
        ]
        pruned = []
        for i in kept_idx:
            it = items[i]
            meta = dict(it.metadata or {})
            meta["rank_score"] = round(order.get(i, 0.0), 4)
            pruned.append(ChatContextItem(source=it.source, title=it.title, content=it.content,
                                          score=it.score, metadata=meta))
        trace = {
            "resolved_scope": f"{request.scope_type.value}:{request.scope_id}",
            "scope_aware": request.scope_type.value != "Advisor",
            "reranker": reranker.describe(),
            "retrieved": retrieved_trace,
            "retrieved_count": len(items), "kept": len(pruned), "pruned": len(items) - len(pruned),
            "top_k": top_k,
        }
        return pruned, trace
