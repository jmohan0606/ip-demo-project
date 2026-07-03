import { apiClient } from "@/lib/api/client";

export interface ContextItem {
  source: string;
  title: string;
  content: string;
  score?: number | null;
}

export interface ChatAnswer {
  answer: string;
  confidence: number;
  reasoning_steps: string[];
  context_items: ContextItem[];
  conversation_id: string;
}

export interface AgenticAnswer {
  answer: string;
  confidence: number;
  final_agent: string;
  reasoning_steps: string[];
  evidence: Array<Record<string, unknown>>;
  tasks: Array<Record<string, unknown>>;
  recommendations: Array<Record<string, unknown>>;
  opportunities: Array<Record<string, unknown>>;
  predictions: Array<Record<string, unknown>>;
}

export function askChat(question: string, advisorId: string): Promise<ChatAnswer> {
  return apiClient.post<ChatAnswer>("/ai-chat/ask", {
    question,
    persona: "Advisor",
    scope_type: "Advisor",
    scope_id: advisorId,
    include_knowledge: true,
    write_to_tigergraph: false,
  });
}

export function runAgentic(question: string, advisorId: string): Promise<AgenticAnswer> {
  return apiClient.post<AgenticAnswer>("/agentic-ai/run", {
    question,
    persona: "Advisor",
    scope_type: "Advisor",
    scope_id: advisorId,
    write_to_memory: false,
    write_to_tigergraph: false,
  });
}
