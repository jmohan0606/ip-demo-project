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
  reason?: string;
}

export interface ScopeComparison {
  revenue_current_12m: number;
  revenue_prior_12m: number;
  revenue_change_pct: number;
}

export interface ScopeSummary {
  scope_type: string;
  scope_id: string;
  totals: ScopeTotals;
  comparison: ScopeComparison;
  child_breakdown: ScopeChild[];
  top_advisors: ScopeTopAdvisor[];
  bottom_advisors: ScopeTopAdvisor[];
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

// --- Executive Dashboard: period + compare-to aware composed payload (12.1) -----
export interface RevenueDriver { category: string; revenue: number; prior_revenue: number; change: number; change_pct: number | null }
export interface MarketRow { scope_type: string; scope_id: string; label: string; revenue_ltm: number; advisor_count: number; rev_per_advisor: number }
export interface BenchmarkRow { scope_id: string; label: string; per_advisor: number; advisor_count: number; is_current: boolean }
export interface TileTrace { source: string; computation: string; link?: string | null }
export interface DashboardTile {
  id: string;
  label: string;
  value: number | null;
  unit: "usd" | "pct" | "count" | "score";
  icon: string;
  delta_pct: number | null;
  delta_unit: "pct" | "pp";
  prior: number | null;
  prior_label: string;
  positive_is_good: boolean;
  trace: TileTrace;
}
export interface RecentTransaction {
  transaction_id: string;
  date: string;
  household: string | null;
  household_id: string | null;
  product: string | null;
  revenue_impact: number;
  type: string;
  advisor_name: string;
}
export interface BenchmarkPeer { advisor_id: string; advisor_name: string; score: number; market: string | null }
export interface BenchmarkMetric {
  metric: string;
  you: number | null;
  peer_avg: number | null;
  vs_peer_pct: number | null;
  unit: string;
  positive_is_good: boolean;
}
export interface ScopeDashboard {
  scope_type: string;
  scope_id: string;
  period: string;
  compare_to: string;
  headline: { revenue: number; delta_pct: number | null; prior?: number | null; basis: string; compare_to: string };
  tiles: DashboardTile[];
  recent_transactions: RecentTransaction[];
  totals: ScopeTotals;
  comparison: ScopeComparison;
  top_advisors: ScopeTopAdvisor[];
  bottom_advisors: ScopeTopAdvisor[];
  child_breakdown: ScopeChild[];
  revenue: {
    monthly_trend: Array<{ month: string; revenue: number }>;
    monthly_trend_prior: Array<{ month: string; revenue: number }>;
    by_business_line: Array<{ category: string; revenue: number }>;
    by_channel: Array<{ channel: string; revenue: number }>;
    revenue_drivers: RevenueDriver[];
    by_geography: Array<{ state: string; revenue: number; advisor_count: number }>;
    kpis: Record<string, number | string | null>;
    comparison: { prior_revenue: number | null; change_pct: number | null; basis: string };
  };
  markets: { top: MarketRow[]; bottom: MarketRow[] };
  benchmark: {
    peer_type: string;
    model?: string;
    current_per_advisor: number;
    firm_per_advisor: number;
    vs_firm_pct: number | null;
    percentile: number | null;
    rows: BenchmarkRow[];
    peers?: BenchmarkPeer[];
    metrics?: BenchmarkMetric[];
    why?: string;
  };
  evidence: ScopeSummary["evidence"];
}

export async function fetchScopeDashboard(
  scopeType: string, scopeId: string, period: string, compareTo: string,
): Promise<ScopeDashboard> {
  const q = new URLSearchParams({ scope_type: scopeType, scope_id: scopeId, period, compare_to: compareTo });
  return apiClient.get<ScopeDashboard>(`/scope/dashboard?${q.toString()}`);
}

export interface ScopeAiInsight {
  scope_type: string;
  scope_id: string;
  period: string;
  insight: import("@/components/patterns/ai-insight-summary").AiInsightData;
  grounding: string;
  grounding_sources?: string[];
}

export async function fetchScopeAiInsight(
  scopeType: string, scopeId: string, period: string, compareTo: string, persona: string,
): Promise<ScopeAiInsight> {
  const q = new URLSearchParams({ scope_type: scopeType, scope_id: scopeId, period, compare_to: compareTo, persona });
  return apiClient.get<ScopeAiInsight>(`/scope/ai-insight?${q.toString()}`);
}
