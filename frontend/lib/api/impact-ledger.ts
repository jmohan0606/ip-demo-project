import { apiClient } from "@/lib/api/client";

export interface LedgerEntry {
  ledger_id: string;
  recommendation_id: string;
  advisor_id: string;
  advisor_name: string;
  recommendation_title: string;
  opportunity_id: string | null;
  action_family: string | null;
  impact_amount: number;
  impact_type: string;
  source_transaction_id: string;
  note: string | null;
  created_ts: string;
}

export interface LedgerTotals {
  total_impact: number;
  completed_count: number;
  advisors_affected: number;
  latest: LedgerEntry | null;
  by_family: Record<string, number>;
  by_advisor: Array<{ advisor_id: string; advisor_name: string; impact: number }>;
}

export interface LedgerResponse {
  entries: LedgerEntry[];
  totals: LedgerTotals;
}

export interface RecLifecycle {
  recommendation_id: string;
  status: string;
  status_note: string | null;
  allowed_actions: string[];
  terminal: boolean;
  transitions: Array<{ from_status: string; to_status: string; action: string; actor_type: string; actor_id: string | null; note: string | null; created_ts: string }>;
  impact: { ledger_id: string; impact_amount: number; source_transaction_id: string; note: string; created_ts: string } | null;
  reasoning_trace_id: string;
}

export async function fetchImpactLedger(advisorId?: string): Promise<LedgerResponse> {
  const path = advisorId && advisorId !== "ALL" ? `/impact-ledger/advisor/${encodeURIComponent(advisorId)}` : "/impact-ledger";
  return apiClient.get<LedgerResponse>(path);
}

export async function fetchRecLifecycle(recommendationId: string): Promise<RecLifecycle> {
  return apiClient.get<RecLifecycle>(`/recommendations/${encodeURIComponent(recommendationId)}/lifecycle`);
}
