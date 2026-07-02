export type HealthStatus = "Healthy" | "Warning" | "Critical" | "Unavailable";

export type ServiceHealth = {
  serviceName: string;
  category: "Agent" | "Graph" | "Vector" | "Database" | "Model" | "API" | "Ingestion" | "Memory";
  status: HealthStatus;
  latencyMs: number;
  successRate: number;
  lastChecked: string;
  mode?: "MCP" | "REST" | "Mock" | "Local";
};

export type AgentRunMetric = {
  agentName: string;
  executions: number;
  successRate: number;
  avgLatencyMs: number;
  failures: number;
  lastRun: string;
};

export type WorkflowTrace = {
  traceId: string;
  workflowName: string;
  status: HealthStatus;
  startedAt: string;
  durationMs: number;
  activeMode: "MCP" | "REST" | "Mock";
  steps: string[];
};

export type CostMetric = {
  metric: string;
  value: string;
  trend: string;
};

export type ErrorEvent = {
  eventId: string;
  source: string;
  severity: "Low" | "Medium" | "High" | "Critical";
  message: string;
  timestamp: string;
  resolution: string;
};
