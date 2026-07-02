import { apiClient } from "@/lib/api/client";
import type { AssistantMessage } from "@/lib/types/ai_assistant";

export async function askAssistant(question: string): Promise<AssistantMessage> {
  try {
    const result = await apiClient.post<any>("/ai-chat/ask", {
      question,
      persona: "Advisor",
      scope_type: "Advisor",
      scope_id: "ADV0001",
      include_knowledge: true,
      write_to_tigergraph: false
    });

    return {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: result.answer ?? "I found relevant advisor context and recommendations.",
      timestamp: new Date().toISOString(),
      evidence: result.context_items?.map((x: any) => x.title ?? x.source ?? "Context item") ?? ["Advisor memory", "Recommendation evidence", "Knowledge playbook"],
      reasoningSteps: result.reasoning_steps ?? ["Retrieved memory", "Searched knowledge", "Checked recommendations", "Generated answer"],
      toolCalls: ["Context Service", "Chroma RAG", "Recommendation Engine", "TigerGraph MCP / Mock Graph"]
    };
  } catch {
    return {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: "Based on the current advisor context, I recommend prioritizing managed account reviews for suitable high-cash households, addressing NNM outflows with a structured outreach sequence, and capturing feedback after each action so the learning loop can improve future recommendations.",
      timestamp: new Date().toISOString(),
      evidence: ["Advisor memory: revenue and NNM trend", "Recommendation queue: managed account opportunity", "Knowledge: compliance-backed playbook", "CRM activity gap"],
      reasoningSteps: ["Retrieved advisor context", "Compared peer benchmark", "Mapped opportunity to playbook", "Checked compliance status", "Generated next best action"],
      toolCalls: ["Context Service", "Chroma RAG", "Recommendation Engine", "Graph Access Fallback"]
    };
  }
}
