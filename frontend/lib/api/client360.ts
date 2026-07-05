import { apiClient } from "@/lib/api/client";

export interface ClientHolding {
  product_id: string;
  product_name: string | null;
  risk_level: string | null;
  managed: boolean;
}

export interface ClientAccount {
  account_id: string;
  account_name: string | null;
  account_type: string | null;
  status: string | null;
  opened_date: string | null;
  current_value: number;
  holdings: ClientHolding[];
}

export interface ClientTransaction {
  transaction_id: string;
  transaction_date: string | null;
  transaction_type: string | null;
  revenue_amount: number;
  gross_amount: number;
}

export interface RecLineage {
  sources: Array<{ type: string; ref: string; detail: string }>;
  reasoning_steps: string[];
  evidence: Array<{ label: string; value: number | string }>;
}

export interface ClientRecommendation {
  recommendation_id: string;
  title: string | null;
  action_text?: string | null;
  recommendation_type?: string | null;
  severity: string | null;
  confidence: number | null;
  priority_score?: number | null;
  estimated_revenue_impact: number | null;
  impact_summary?: string | null;
  status: string | null;
  lineage?: RecLineage;
}

export interface SimilarBlock {
  source: { entity_id: string; name: string; [k: string]: unknown } | null;
  matches: Array<{ entity_id: string; name: string; similarity: number; [k: string]: unknown }>;
}

export interface ClientProfile {
  household_id: string;
  household_name: string;
  segment: string | null;
  risk_profile: string | null;
  status: string | null;
  state: string | null;
  total_aum: number;
  serving_advisor: { advisor_id: string | null; advisor_name: string | null };
  summary: {
    account_count: number;
    holding_count: number;
    managed_value: number;
    managed_ratio: number;
    transaction_count: number;
    revenue_ltm: number;
  };
  accounts: ClientAccount[];
  transactions: ClientTransaction[];
  recommendations: ClientRecommendation[];
  similar?: { households: SimilarBlock | null; accounts: SimilarBlock | null };
  evidence: { source: string };
}

export interface HouseholdRef {
  household_id: string;
  household_name: string;
  segment: string | null;
  total_aum: number | null;
}

export async function fetchHouseholdsForAdvisor(advisorId: string): Promise<HouseholdRef[]> {
  const d = await apiClient.get<{ households: HouseholdRef[] }>(`/client/households/${advisorId}`);
  return d.households ?? [];
}

export async function fetchClientProfile(householdId: string): Promise<ClientProfile> {
  return apiClient.get<ClientProfile>(`/client/360/${householdId}`);
}
