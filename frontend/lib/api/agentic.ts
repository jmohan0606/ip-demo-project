import { apiClient } from "@/lib/api/client";

export interface AgentTask {
  task_id: string;
  agent_name: string;
  instruction: string;
  status: string;
  result?: Record<string, unknown>;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface AgentEvidence {
  source: string;
  title: string;
  content: string;
  score: number | null;
  metadata?: Record<string, unknown>;
}

export interface ConfidenceBreakdown {
  confidence: number;
  formula: string;
  components: {
    task_success_rate: number;
    evidence_coverage: number;
    llm_authored: boolean;
    model_confidence: number;
    model_confidence_source: string;
  };
}

export interface ComplianceReview {
  reviews: Array<{
    recommendation_id: string | null;
    status: string;
    flags: Array<{ rule: string; level: string; detail: string }>;
    rules_evaluated: string[];
  }>;
  status_counts: Record<string, number>;
  rules_evaluated: string[];
}

export interface AgenticRun {
  run_id: string;
  answer: string;
  final_agent: string;
  tasks: AgentTask[];
  evidence: AgentEvidence[];
  reasoning_steps: string[];
  confidence: number;
  confidence_breakdown: ConfidenceBreakdown | null;
  route_plan: string[];
  graph_evidence: {
    query?: string;
    served_by?: string;
    served_by_tier?: number;
    counts?: Record<string, number>;
  } | null;
  compliance_review: ComplianceReview | null;
  errors: string[];
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
