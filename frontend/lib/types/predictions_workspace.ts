export type ForecastMetric = "Revenue" | "NNM" | "AUM" | "AGP Goal" | "Opportunity" | "Churn Risk" | "Growth Potential";

export type ForecastPoint = {
  period: string;
  baseline: number;
  forecast: number;
  lowerBound: number;
  upperBound: number;
};

export type PredictionModelCard = {
  modelId: string;
  name: string;
  modelType: "Scikit-Learn" | "GNN" | "Graph Embedding" | "Rules + ML";
  target: ForecastMetric;
  confidence: number;
  status: "Active" | "Fallback" | "Training Required";
  explanation: string;
};

export type PredictionDriver = {
  driver: string;
  contribution: number;
  direction: "Positive" | "Negative" | "Neutral";
};
