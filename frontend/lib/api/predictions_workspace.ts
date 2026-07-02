import type { ForecastPoint, PredictionDriver, PredictionModelCard } from "@/lib/types/predictions_workspace";

export function getForecastSeries(): ForecastPoint[] {
  return [
    { period: "Jul", baseline: 460000, forecast: 488000, lowerBound: 452000, upperBound: 512000 },
    { period: "Aug", baseline: 468000, forecast: 501000, lowerBound: 463000, upperBound: 529000 },
    { period: "Sep", baseline: 472000, forecast: 516000, lowerBound: 475000, upperBound: 545000 },
    { period: "Oct", baseline: 481000, forecast: 529000, lowerBound: 486000, upperBound: 560000 },
    { period: "Nov", baseline: 490000, forecast: 548000, lowerBound: 502000, upperBound: 581000 },
    { period: "Dec", baseline: 505000, forecast: 572000, lowerBound: 521000, upperBound: 612000 }
  ];
}

export function getPredictionModels(): PredictionModelCard[] {
  return [
    { modelId: "PRED-REV-001", name: "Revenue Forecast", modelType: "Scikit-Learn", target: "Revenue", confidence: 0.87, status: "Active", explanation: "Uses revenue history, product mix, CRM activity, peer benchmark and AGP signals." },
    { modelId: "PRED-NNM-001", name: "NNM Forecast", modelType: "Graph Embedding", target: "NNM", confidence: 0.82, status: "Active", explanation: "Uses household behavior, transaction flows, CRM engagement and advisor similarity." },
    { modelId: "PRED-AUM-001", name: "AUM Forecast", modelType: "Rules + ML", target: "AUM", confidence: 0.79, status: "Fallback", explanation: "Uses AUM trend, NCF, NNM and market-adjusted growth assumptions." },
    { modelId: "PRED-GNN-001", name: "Opportunity Propensity", modelType: "GNN", target: "Opportunity", confidence: 0.84, status: "Active", explanation: "Uses graph neighborhood, household-product links, similar advisors and opportunity outcomes." }
  ];
}

export function getPredictionDrivers(): PredictionDriver[] {
  return [
    { driver: "Managed revenue mix", contribution: 31, direction: "Positive" },
    { driver: "CRM meeting cadence", contribution: 18, direction: "Positive" },
    { driver: "NNM outflow concentration", contribution: -16, direction: "Negative" },
    { driver: "AGP goal attainment", contribution: 12, direction: "Positive" },
    { driver: "Brokerage compression", contribution: -9, direction: "Negative" }
  ];
}
