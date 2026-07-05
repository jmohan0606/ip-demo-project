import { apiClient } from "@/lib/api/client";

export interface ScopeStatusDistribution {
  on_track: number;
  attention: number;
  urgent: number;
  critical: number;
}

export interface ScopeTotals {
  advisor_count: number;
  advisors_with_data: number;
  revenue_ltm: number;
  aum_total: number;
  nnm_annualized: number;
  managed_revenue: number;
  avg_goal_attainment: number;
  avg_agp_risk_score: number;
  status_distribution: ScopeStatusDistribution;
}

export interface ScopeChild {
  scope_type: string;
  scope_id: string;
  label: string;
  advisor_count: number;
  revenue_ltm: number;
  aum_total: number;
  avg_goal_attainment: number;
}

export interface ScopeTopAdvisor {
  advisor_id: string;
  advisor_name: string;
  revenue_ltm: number;
  aum_total: number;
  goal_attainment: number | null;
  agp_risk_score: number | null;
  status: string;
}

export interface ScopeSummary {
  scope_type: string;
  scope_id: string;
  totals: ScopeTotals;
  child_breakdown: ScopeChild[];
  top_advisors: ScopeTopAdvisor[];
  evidence: {
    source: string;
    advisor_ids_resolved: number;
    advisor_ids_sample: string[];
    computation: string;
  };
}

/** Scope-aware rollup for the command center: aggregates every advisor's real
 * feature snapshot under the given hierarchy scope. Scope type/id come from the
 * shell breadcrumb, so changing scope reshapes the whole page from real data. */
export async function fetchScopeSummary(scopeType: string, scopeId: string): Promise<ScopeSummary> {
  return apiClient.get<ScopeSummary>(
    `/scope/summary?scope_type=${encodeURIComponent(scopeType)}&scope_id=${encodeURIComponent(scopeId)}`,
  );
}
