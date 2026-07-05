from __future__ import annotations

from app.agents.nodes.compliance_agent import ComplianceAgent
from app.ai.chat.context_assembler import ChatContextAssembler
from app.llm.client import get_llm_client
from app.models.ai_chat import ChatRequest, ChatResponse
from app.shared.ids import timestamp_id


class AiAssistantChatEngine:
    def __init__(self) -> None:
        self.context_assembler = ChatContextAssembler()
        self.llm = get_llm_client()  # Section 2 adapter: mock | claude | real

    def answer(self, request: ChatRequest) -> ChatResponse:
        conversation_id = request.conversation_id or timestamp_id("conv")
        turn_id = timestamp_id("chatturn")
        context_items = self.context_assembler.assemble(request)

        # COMP-001 request-level guardrail: screen the user's question for prohibited
        # performance claims BEFORE answering, reusing the same term list the ComplianceAgent
        # applies to generated recommendations. A hit produces a visible block in the answer.
        compliance_block = self._compliance_screen(request.question)

        prompt_context = "\n\n".join(
            f"[{item.source.value}] {item.title}\n{item.content}"
            for item in context_items[:12]
        )

        prompt = f"""
Question:
{request.question}

Persona:
{request.persona.value}

Scope:
{request.scope_type.value} {request.scope_id}

Context:
{prompt_context}

Instructions:
Answer with evidence. Include what data was used and what next action should be taken.
"""

        raw_answer = self.llm.generate(
            prompt,
            {"system_prompt": "You are iPerform Insights & Coaching AI Assistant. "
                              "Answer using only the provided context; cite concrete figures."},
        )

        # Mock adapter gives generic answer, so augment with deterministic evidence response.
        answer = self._grounded_answer(request, context_items, raw_answer, compliance_block)

        reasoning_steps = [
            "Resolved persona and scope.",
            "Screened the request against COMP-001 prohibited-claim rules.",
            "Retrieved context memory.",
            "Retrieved knowledge/RAG snippets where available.",
            "Retrieved/generated insight context.",
            "Retrieved predictions, opportunities and recommendations.",
            "Generated grounded assistant answer.",
            "Persisted conversation to memory when enabled.",
        ]
        if compliance_block:
            reasoning_steps.insert(2, f"COMP-001 BLOCK raised: prohibited claim {compliance_block['terms']}.")

        return ChatResponse(
            conversation_id=conversation_id,
            conversation_turn_id=turn_id,
            answer=answer,
            persona=request.persona,
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            context_items=context_items,
            reasoning_steps=reasoning_steps,
            confidence=(0.99 if compliance_block else (0.82 if context_items else 0.55)),
        )

    @staticmethod
    def _compliance_screen(question: str) -> dict | None:
        text = (question or "").lower()
        hits = [t for t in ComplianceAgent.PROHIBITED_CLAIMS if t in text]
        return {"rule": "COMP-001", "level": "BLOCK", "terms": hits} if hits else None

    def _grounded_answer(self, request: ChatRequest, items, raw_answer: str, compliance_block: dict | None = None) -> str:
        recs = [i for i in items if i.source.value == "Recommendations"]
        opps = [i for i in items if i.source.value == "Opportunities"]
        preds = [i for i in items if i.source.value == "Predictions"]
        insights = [i for i in items if i.source.value == "Insights"]
        memory = [i for i in items if i.source.value == "Context Memory"]

        lines: list[str] = []
        if compliance_block:
            term = compliance_block["terms"][0]
            lines.extend([
                f"⛔ Compliance block (COMP-001): this request references a prohibited performance "
                f'claim ("{term}"). I can\'t advise offering, marketing, or recommending a product on a '
                "guaranteed-return / risk-free / no-loss basis — that violates COMP-001 (prohibited "
                "performance claims) and firm supervisory policy.",
                "",
                "What you can do: present products with balanced, suitability-documented disclosures of "
                "risk and expected return, and route any performance representations through compliance "
                "review before client contact.",
                "",
            ])
        lines.extend([
            f"For {request.scope_type.value} {request.scope_id}, here is the grounded answer:",
            "",
        ])
        if insights:
            lines.append(f"Insight summary: {insights[0].content}")
        if recs:
            lines.append(f"Top recommendation: {recs[0].content}")
        if opps:
            lines.append(f"Top opportunity: {opps[0].title} — {opps[0].content}")
        if preds:
            lines.append(f"Prediction signal: {preds[0].title} — {preds[0].content}")
        if memory and memory[0].content and "No relevant memories" not in memory[0].content:
            lines.append("Relevant memory was used to preserve prior context.")
        lines.extend([
            "",
            "Next action: review the evidence and, if the recommendation is accepted or completed, capture feedback so future ranking can improve.",
        ])
        if raw_answer and "[mock-llm" not in raw_answer:
            lines.extend(["", "AI generated note:", raw_answer])
        return "\n".join(lines)
