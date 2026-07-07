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

export interface AskScope {
  scopeType: string; // Firm | Division | Region | Market | Advisor — the REAL active scope
  scopeId: string;
  persona: string; // Advisor | MDW | DDW | Firm (backend ChatPersona)
}

/** Map the shell persona to the backend's ChatPersona vocabulary. */
export function toChatPersona(shellPersona: string, scopeType: string): string {
  if (scopeType === "Advisor") return "Advisor";
  if (shellPersona === "MDW") return "MDW";
  if (shellPersona === "DDW") return "DDW";
  return scopeType === "Firm" ? "Firm" : shellPersona === "Advisor" ? "Advisor" : shellPersona;
}

/** §11.6 — the assistant follows the ACTIVE scope: a DDW asking at Division scope gets
 * real rollup reasoning across the division, never one resolved advisor's story. */
export function askChat(question: string, scope: AskScope): Promise<ChatAnswer> {
  return apiClient.post<ChatAnswer>("/ai-chat/ask", {
    question,
    persona: toChatPersona(scope.persona, scope.scopeType),
    scope_type: scope.scopeType,
    scope_id: scope.scopeId,
    include_knowledge: true,
    write_to_tigergraph: false,
  });
}

export function runAgentic(question: string, scope: AskScope): Promise<AgenticAnswer> {
  return apiClient.post<AgenticAnswer>("/agentic-ai/run", {
    question,
    persona: toChatPersona(scope.persona, scope.scopeType),
    scope_type: scope.scopeType,
    scope_id: scope.scopeId,
    write_to_memory: false,
    write_to_tigergraph: false,
  });
}
