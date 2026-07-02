export type ExecutiveKpi = {
  id: string;
  label: string;
  value: string;
  change: string;
  trend: "up" | "down" | "flat";
  description: string;
  tone: "default" | "insight" | "risk";
};

export type PerformancePoint = {
  period: string;
  revenue: number;
  aum: number;
  nnm: number;
  ncf: number;
};

export type ProductMixPoint = {
  category: string;
  revenue: number;
  growth: number;
  share: number;
};

export type PerformerRow = {
  rank: number;
  advisorId: string;
  advisorName: string;
  market: string;
  revenue: number;
  growth: number;
  agpStatus: "On Track" | "At Risk" | "Off Track" | "Not AGP";
};

export type CoachingInsight = {
  id: string;
  title: string;
  severity: "High" | "Medium" | "Low";
  confidence: number;
  summary: string;
  evidence: string[];
  reasoningSteps: string[];
  recommendedActions: string[];
};

export type ExecutiveDashboardPayload = {
  scopeLabel: string;
  periodLabel: string;
  kpis: ExecutiveKpi[];
  performanceTrend: PerformancePoint[];
  productMix: ProductMixPoint[];
  topPerformers: PerformerRow[];
  bottomPerformers: PerformerRow[];
  insights: CoachingInsight[];
};
