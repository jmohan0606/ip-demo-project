import { apiClient } from "@/lib/api/client";

export interface WhatIfLevers {
  meeting_increase_pct: number;
  prospecting_increase_pct: number;
  aum_growth_pct: number;
  goal_reviews_added: number;
  horizon_months: number;
}

export interface WhatIfMetric {
  metric: string;
  unit: string;
  current: number;
  projected: number;
  change: number;
  change_pct: number | null;
  formula: string;
}

export interface WhatIfResult {
  advisor_id: string;
  snapshot_id: string | null;
  horizon_months: number;
  levers: Record<string, number>;
  baseline_features: Record<string, number>;
  metrics: WhatIfMetric[];
  elasticities: Record<string, number>;
  note: string;
}

/** Projects an advisor's REAL current feature snapshot forward under the
 * scenario levers via the backend /whatif/simulate endpoint. No fabricated
 * baselines — every current value is the advisor's actual feature value and
 * each projected metric carries its computation formula as evidence. */
export async function simulateWhatIf(
  advisorId: string,
  levers: WhatIfLevers,
): Promise<WhatIfResult> {
  return apiClient.post<WhatIfResult>("/whatif/simulate", {
    advisor_id: advisorId,
    ...levers,
  });
}
