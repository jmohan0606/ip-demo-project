import type { AgentRunMetric, CostMetric, ErrorEvent, ServiceHealth, WorkflowTrace } from "@/lib/types/observability";

export function getServiceHealth(): ServiceHealth[] {
  return [
    { serviceName: "Supervisor Agent", category: "Agent", status: "Healthy", latencyMs: 182, successRate: 99.1, lastChecked: "Just now", mode: "Local" },
    { serviceName: "Context Agent", category: "Agent", status: "Healthy", latencyMs: 241, successRate: 98.7, lastChecked: "Just now", mode: "Local" },
    { serviceName: "Recommendation Agent", category: "Agent", status: "Healthy", latencyMs: 332, successRate: 97.9, lastChecked: "Just now", mode: "Local" },
    { serviceName: "TigerGraph MCP", category: "Graph", status: "Warning", latencyMs: 0, successRate: 0, lastChecked: "Not configured", mode: "Mock" },
    { serviceName: "TigerGraph REST Fallback", category: "Graph", status: "Warning", latencyMs: 0, successRate: 0, lastChecked: "Not configured", mode: "Mock" },
    { serviceName: "Mock Graph Service", category: "Graph", status: "Healthy", latencyMs: 45, successRate: 100, lastChecked: "Just now", mode: "Mock" },
    { serviceName: "Chroma RAG", category: "Vector", status: "Healthy", latencyMs: 142, successRate: 98.2, lastChecked: "Just now", mode: "Local" },
    { serviceName: "SQLite Feature Store", category: "Database", status: "Healthy", latencyMs: 64, successRate: 99.8, lastChecked: "Just now", mode: "Local" },
    { serviceName: "Prediction Engine", category: "Model", status: "Healthy", latencyMs: 211, successRate: 97.2, lastChecked: "Just now", mode: "Local" },
    { serviceName: "Memory Service", category: "Memory", status: "Healthy", latencyMs: 126, successRate: 98.9, lastChecked: "Just now", mode: "Local" },
    { serviceName: "FastAPI Backend", category: "API", status: "Healthy", latencyMs: 88, successRate: 99.4, lastChecked: "Just now", mode: "Local" },
    { serviceName: "Data Ingestion", category: "Ingestion", status: "Healthy", latencyMs: 390, successRate: 96.8, lastChecked: "2 min ago", mode: "Local" }
  ];
}

export function getAgentMetrics(): AgentRunMetric[] {
  return [
    { agentName: "Supervisor Agent", executions: 218, successRate: 99.1, avgLatencyMs: 182, failures: 2, lastRun: "Just now" },
    { agentName: "Context Retrieval Agent", executions: 204, successRate: 98.7, avgLatencyMs: 241, failures: 3, lastRun: "Just now" },
    { agentName: "Graph Agent", executions: 196, successRate: 97.8, avgLatencyMs: 388, failures: 4, lastRun: "1 min ago" },
    { agentName: "Prediction Agent", executions: 177, successRate: 97.2, avgLatencyMs: 296, failures: 5, lastRun: "2 min ago" },
    { agentName: "Recommendation Agent", executions: 184, successRate: 97.9, avgLatencyMs: 332, failures: 4, lastRun: "Just now" },
    { agentName: "Explainability Agent", executions: 171, successRate: 98.4, avgLatencyMs: 219, failures: 3, lastRun: "Just now" }
  ];
}

export function getWorkflowTraces(): WorkflowTrace[] {
  return [
    { traceId: "TRC-001", workflowName: "Advisor Coaching Question", status: "Healthy", startedAt: "2026-06-17 10:22", durationMs: 1380, activeMode: "Mock", steps: ["Supervisor", "Context", "Graph", "Prediction", "Recommendation", "Explainability", "AI Assistant"] },
    { traceId: "TRC-002", workflowName: "Recommendation Generation", status: "Healthy", startedAt: "2026-06-17 10:18", durationMs: 1142, activeMode: "Mock", steps: ["Context", "Opportunity", "Compliance", "Recommendation", "Memory"] },
    { traceId: "TRC-003", workflowName: "Feedback Learning", status: "Warning", startedAt: "2026-06-17 10:11", durationMs: 1720, activeMode: "Mock", steps: ["Feedback", "Learning Signal", "Memory Update", "Graph Write Fallback"] }
  ];
}

export function getCostMetrics(): CostMetric[] {
  return [
    { metric: "Estimated Tokens", value: "42.8K", trend: "+8.4%" },
    { metric: "Agent Calls", value: "1,150", trend: "+12.1%" },
    { metric: "Avg Latency", value: "1.38s", trend: "-4.2%" },
    { metric: "Fallback Rate", value: "18%", trend: "MCP pending" }
  ];
}

export function getErrorEvents(): ErrorEvent[] {
  return [
    { eventId: "ERR-001", source: "TigerGraph MCP", severity: "Medium", message: "MCP server not configured; mock fallback active.", timestamp: "2026-06-17 10:20", resolution: "Configure MCP endpoint and credentials." },
    { eventId: "ERR-002", source: "REST Fallback", severity: "Low", message: "REST fallback disabled during local UI demo.", timestamp: "2026-06-17 10:19", resolution: "Enable REST only after MCP validation plan." },
    { eventId: "ERR-003", source: "Data Ingestion", severity: "Low", message: "Checkpoint validation used local runtime simulation.", timestamp: "2026-06-17 10:10", resolution: "Run live TigerGraph ingestion validation." }
  ];
}
