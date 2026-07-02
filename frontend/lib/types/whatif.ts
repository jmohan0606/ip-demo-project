export type ScenarioAssumptions = {
  meetingIncreasePct: number;
  prospectConversionIncreasePct: number;
  managedRevenueShiftPct: number;
  nnmIncreasePct: number;
  aumIncreasePct: number;
  productMixShiftPct: number;
};

export type ScenarioImpact = {
  baselineRevenue: number;
  projectedRevenue: number;
  baselineNnm: number;
  projectedNnm: number;
  baselineAum: number;
  projectedAum: number;
  baselineGoalAttainment: number;
  projectedGoalAttainment: number;
  agpStatusBefore: "On Track" | "At Risk" | "Off Track" | "Not AGP";
  agpStatusAfter: "On Track" | "At Risk" | "Off Track" | "Not AGP";
};

export type SavedScenario = {
  scenarioId: string;
  name: string;
  createdAt: string;
  assumptions: ScenarioAssumptions;
  impact: ScenarioImpact;
  aiExplanation: string;
};
