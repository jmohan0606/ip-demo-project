from __future__ import annotations

from app.llm import get_llm_runtime
from app.llm.prompt_templates import build_agent_prompt
from app.memory import get_memory_runtime
from app.recommendations import get_recommendation_runtime


class AiAssistantRuntime:
    def __init__(self) -> None:
        self.llm = get_llm_runtime()
        self.memory = get_memory_runtime()
        self.recommendations = get_recommendation_runtime()

    def status(self) -> dict:
        return {
            "assistant_runtime": "active",
            "llm": self.llm.status(),
            "memory": self.memory.status(),
        }

    def ask(self, context: dict, question: str) -> dict:
        context_packet = self.memory.build_context_packet(context, question, max_tokens=1200)
        messages = build_agent_prompt(question, context_packet, workflow="ai_assistant")
        llm_response = self.llm.chat(messages, temperature=0.2).to_dict()
        memory_write = self.memory.write_memory({
            **context,
            "memory_type": "Conversation",
            "title": f"AI Assistant question: {question[:80]}",
            "content": f"Question: {question}\nAnswer: {llm_response.get('content', '')[:1000]}",
            "importance": 0.75,
            "tags": ["ai-assistant", "conversation"],
        })
        return {
            "answer": llm_response.get("content", ""),
            "llm": llm_response,
            "context_packet": context_packet,
            "memory_write": memory_write,
            "agent_trace": {
                "workflow": "ai_assistant",
                "agents": [
                    {"agent_name": "SupervisorAgent", "status": "completed"},
                    {"agent_name": "ContextAgent", "status": "completed"},
                    {"agent_name": "MemoryAgent", "status": "completed"},
                    {"agent_name": "KnowledgeAgent", "status": "completed"},
                    {"agent_name": "GraphAgent", "status": "completed"},
                    {"agent_name": "LlmReasoningAgent", "status": "completed"},
                    {"agent_name": "MemoryWritebackAgent", "status": "completed"},
                ],
            },
        }

    def recommendation_narrative(self, context: dict) -> dict:
        payload = self.recommendations.generate(context)
        messages = build_agent_prompt(
            "Summarize the top recommendation and why it matters.",
            {
                "compressed_context": str(payload)[:6000],
            },
            workflow="recommendation_narrative",
        )
        llm_response = self.llm.chat(messages, temperature=0.2).to_dict()
        return {"recommendations": payload, "narrative": llm_response}


_ai_assistant_runtime: AiAssistantRuntime | None = None


def get_ai_assistant_runtime() -> AiAssistantRuntime:
    global _ai_assistant_runtime
    if _ai_assistant_runtime is None:
        _ai_assistant_runtime = AiAssistantRuntime()
    return _ai_assistant_runtime
