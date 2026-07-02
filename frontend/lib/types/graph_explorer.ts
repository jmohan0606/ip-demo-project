export type GraphNodeType =
  | "Advisor"
  | "Household"
  | "Account"
  | "Product"
  | "Opportunity"
  | "Recommendation"
  | "Memory"
  | "Transaction";

export type GraphExplorerNode = {
  id: string;
  label: string;
  type: GraphNodeType;
  score?: number;
  description?: string;
};

export type GraphExplorerEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  weight?: number;
};

export type GraphExplorerPayload = {
  nodes: GraphExplorerNode[];
  edges: GraphExplorerEdge[];
};
