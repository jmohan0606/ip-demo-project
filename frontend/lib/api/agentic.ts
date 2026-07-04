import { apiClient } from "@/lib/api/client";

export interface AgentTask {
  task_id: string;
  agent_name: string;
  instruction: string;
  status: string;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface AgentEvidence {
  source: string;
  title: string;
  content: string;
  score: number | null;
}

export interface AgenticRun {
  run_id: string;
  answer: string;
  final_agent: string;
  tasks: AgentTask[];
  evidence: AgentEvidence[];
  reasoning_steps: string[];
  confidence: number;
  created_at: string;
}

export async function runAgenticWorkflow(question: string, advisorId: string): Promise<AgenticRun> {
  // The agentic workflow keys off scope_id/scope_type (not advisor_id) — every
  // agent reads state.request.scope_id as the advisor, so send those fields or
  // the run silently falls back to the default advisor.
  return apiClient.post<AgenticRun>("/agentic-ai/run", {
    question,
    scope_type: "Advisor",
    scope_id: advisorId,
  });
}
