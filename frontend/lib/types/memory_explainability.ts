export type MemoryType =
  | "Episodic"
  | "Semantic"
  | "Reasoning"
  | "Short-Term"
  | "Long-Term"
  | "Conversation"
  | "Recommendation"
  | "Feedback";

export type MemoryTimelineItem = {
  memoryId: string;
  memoryType: MemoryType;
  timestamp: string;
  title: string;
  summary: string;
  sourceAgent: string;
  importanceScore: number;
  linkedObject?: string;
};

export type ExplainabilityPathStep = {
  stepId: string;
  label: string;
  nodeType: "Memory" | "Graph Node" | "Document" | "Feature" | "Prediction" | "Opportunity" | "Recommendation" | "Feedback";
  description: string;
  confidence: number;
};

export type AgentTraceStep = {
  agentName: string;
  status: "Completed" | "Running" | "Failed" | "Skipped";
  input: string;
  output: string;
  durationMs: number;
  toolCalls: string[];
};

export type ToolCallAudit = {
  toolName: string;
  system: "TigerGraph MCP" | "TigerGraph REST" | "Chroma" | "Feature Store" | "Prediction Engine" | "Recommendation Engine";
  status: "Success" | "Fallback" | "Failed";
  durationMs: number;
  resultSize: string;
};

export type LearningLoopItem = {
  recommendationId: string;
  action: "Accepted" | "Rejected" | "Modified" | "Completed";
  outcome: string;
  learningSignal: string;
  memoryUpdate: string;
};
