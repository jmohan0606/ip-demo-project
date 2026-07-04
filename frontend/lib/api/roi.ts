import { apiClient } from "@/lib/api/client";

export interface LearningTrendPoint {
  round: number;
  advisor_id: string;
  action: string;
  action_family: string;
  accepted: number;
  rejected: number;
  cumulative_reward: number;
  captured_impact: number;
}

export interface ImpactTrend {
  advisor_ids: string[];
  event_count: number;
  trend: LearningTrendPoint[];
  totals: {
    accepted: number;
    implemented: number;
    rejected: number;
    modified: number;
    ignored: number;
    cumulative_reward: number;
    captured_impact: number;
  };
  final_weights: Array<{ family: string; weight: number; events: number }>;
  note?: string;
}

export interface Recommendation {
  recommendation_id: string;
  title: string;
  action_text: string;
  action_family: string;
  base_priority_score: number;
  learning_weight: number;
  priority_score: number;
  severity: string;
  confidence: number;
  estimated_revenue_impact: number;
  status: string;
}

export async function fetchImpactTrend(): Promise<ImpactTrend> {
  return apiClient.get<ImpactTrend>("/feedback-learning/impact-trend");
}

export async function generateRecommendations(advisorId: string): Promise<Recommendation[]> {
  const d = await apiClient.post<{ recommendations: Recommendation[] }>(`/recommendations/generate/${advisorId}`);
  return d.recommendations ?? [];
}
