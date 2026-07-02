export type OpportunityCard = {
  opportunityId: string;
  title: string;
  advisorName: string;
  householdName: string;
  opportunityType: string;
  priority: "High" | "Medium" | "Low";
  score: number;
  expectedRevenueImpact: number;
  expectedNnmImpact: number;
  evidence: string[];
};

export type RecommendationCard = {
  recommendationId: string;
  opportunityId: string;
  title: string;
  actionText: string;
  complianceStatus: "Passed" | "Review Required" | "Blocked";
  confidence: number;
  expectedImpact: number;
  status: "Generated" | "Accepted" | "Rejected" | "Modified" | "Completed";
  reasoningSteps: string[];
};
