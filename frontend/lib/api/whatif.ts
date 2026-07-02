import type { ScenarioAssumptions, ScenarioImpact } from "@/lib/types/whatif";

export function simulateScenario(assumptions: ScenarioAssumptions): ScenarioImpact {
  const baselineRevenue = 4800000;
  const baselineNnm = 42500000;
  const baselineAum = 812000000;
  const baselineGoalAttainment = 83;

  const revenueLift =
    assumptions.meetingIncreasePct * 0.18 +
    assumptions.prospectConversionIncreasePct * 0.24 +
    assumptions.managedRevenueShiftPct * 0.31 +
    assumptions.productMixShiftPct * 0.12;

  const nnmLift = assumptions.nnmIncreasePct * 0.72 + assumptions.meetingIncreasePct * 0.08;
  const aumLift = assumptions.aumIncreasePct * 0.82 + assumptions.nnmIncreasePct * 0.05;
  const goalLift = assumptions.meetingIncreasePct * 0.12 + assumptions.prospectConversionIncreasePct * 0.18;

  const projectedGoalAttainment = Math.min(100, baselineGoalAttainment + goalLift);

  return {
    baselineRevenue,
    projectedRevenue: baselineRevenue * (1 + revenueLift / 100),
    baselineNnm,
    projectedNnm: baselineNnm * (1 + nnmLift / 100),
    baselineAum,
    projectedAum: baselineAum * (1 + aumLift / 100),
    baselineGoalAttainment,
    projectedGoalAttainment,
    agpStatusBefore: "At Risk",
    agpStatusAfter: projectedGoalAttainment >= 90 ? "On Track" : projectedGoalAttainment >= 80 ? "At Risk" : "Off Track"
  };
}

export function explainScenario(assumptions: ScenarioAssumptions, impact: ScenarioImpact): string {
  const revenueDelta = impact.projectedRevenue - impact.baselineRevenue;
  const nnmDelta = impact.projectedNnm - impact.baselineNnm;
  return `The scenario improves projected revenue by $${Math.round(revenueDelta).toLocaleString()} and projected NNM by $${Math.round(nnmDelta).toLocaleString()}. The largest drivers are managed revenue mix shift, prospect conversion improvement, and meeting cadence. AGP status moves from ${impact.agpStatusBefore} to ${impact.agpStatusAfter}.`;
}
