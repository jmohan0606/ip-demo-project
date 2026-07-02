import type {
  AgentTraceStep,
  ExplainabilityPathStep,
  LearningLoopItem,
  MemoryTimelineItem,
  ToolCallAudit
} from "@/lib/types/memory_explainability";

export function getMemoryTimeline(): MemoryTimelineItem[] {
  return [
    {
      memoryId: "MEM-001",
      memoryType: "Conversation",
      timestamp: "2026-05-01",
      title: "Advisor asked about revenue decline",
      summary: "Captured advisor question and scope context for Avery Morgan.",
      sourceAgent: "AI Assistant Agent",
      importanceScore: 0.78,
      linkedObject: "ADV0001"
    },
    {
      memoryId: "MEM-002",
      memoryType: "Reasoning",
      timestamp: "2026-05-03",
      title: "Revenue mix gap detected",
      summary: "Reasoning memory stored peer benchmark gap in managed account penetration.",
      sourceAgent: "Explainability Agent",
      importanceScore: 0.91,
      linkedObject: "REC-001"
    },
    {
      memoryId: "MEM-003",
      memoryType: "Recommendation",
      timestamp: "2026-05-05",
      title: "Managed account recommendation generated",
      summary: "Recommendation generated from opportunity, suitability and product mix evidence.",
      sourceAgent: "Recommendation Agent",
      importanceScore: 0.88,
      linkedObject: "REC-001"
    },
    {
      memoryId: "MEM-004",
      memoryType: "Feedback",
      timestamp: "2026-05-10",
      title: "Recommendation accepted",
      summary: "Advisor accepted managed account review recommendation.",
      sourceAgent: "Feedback Learning Agent",
      importanceScore: 0.84,
      linkedObject: "LS-001"
    },
    {
      memoryId: "MEM-005",
      memoryType: "Long-Term",
      timestamp: "2026-05-20",
      title: "Learning signal updated future recommendations",
      summary: "Positive outcome increased weight for managed account review playbook in similar households.",
      sourceAgent: "Memory Agent",
      importanceScore: 0.93,
      linkedObject: "PLAYBOOK-MA-001"
    }
  ];
}

export function getExplainabilityPath(): ExplainabilityPathStep[] {
  return [
    { stepId: "EXP-001", label: "Revenue Mix Gap", nodeType: "Feature", description: "Managed revenue share is below peer benchmark.", confidence: 0.89 },
    { stepId: "EXP-002", label: "Peer Benchmark Gap", nodeType: "Graph Node", description: "Advisor is 6 percentage points below market peer average.", confidence: 0.86 },
    { stepId: "EXP-003", label: "Household Suitability", nodeType: "Graph Node", description: "Parker Family Trust has suitable risk profile and liquidity position.", confidence: 0.91 },
    { stepId: "EXP-004", label: "Compliance Playbook", nodeType: "Document", description: "Managed account review playbook supports recommended action.", confidence: 0.87 },
    { stepId: "EXP-005", label: "Recommendation", nodeType: "Recommendation", description: "Schedule managed account review with evidence and documentation.", confidence: 0.88 }
  ];
}

export function getAgentTrace(): AgentTraceStep[] {
  return [
    { agentName: "Supervisor Agent", status: "Completed", input: "Advisor asks why revenue is low.", output: "Route to context, graph, prediction and recommendation agents.", durationMs: 182, toolCalls: ["LangGraph Router"] },
    { agentName: "Context Retrieval Agent", status: "Completed", input: "Scope ADV0001", output: "Retrieved memory and prior feedback.", durationMs: 241, toolCalls: ["Context Service", "TigerGraph MCP"] },
    { agentName: "Graph Agent", status: "Completed", input: "Advisor / household graph", output: "Found household opportunity path.", durationMs: 388, toolCalls: ["TigerGraph MCP", "Graph Traversal"] },
    { agentName: "Prediction Agent", status: "Completed", input: "Feature vector", output: "Revenue forecast and NNM risk.", durationMs: 296, toolCalls: ["Feature Store", "Prediction Engine"] },
    { agentName: "Recommendation Agent", status: "Completed", input: "Opportunity + prediction", output: "Generated managed account review recommendation.", durationMs: 332, toolCalls: ["Recommendation Engine", "Compliance Check"] },
    { agentName: "Explainability Agent", status: "Completed", input: "Evidence bundle", output: "Generated reasoning chain and evidence panel.", durationMs: 219, toolCalls: ["Evidence Builder"] }
  ];
}

export function getToolAudit(): ToolCallAudit[] {
  return [
    { toolName: "getAdvisorContext", system: "TigerGraph MCP", status: "Success", durationMs: 188, resultSize: "12 nodes / 19 edges" },
    { toolName: "searchKnowledge", system: "Chroma", status: "Success", durationMs: 142, resultSize: "4 chunks" },
    { toolName: "getFeatureVector", system: "Feature Store", status: "Success", durationMs: 64, resultSize: "38 features" },
    { toolName: "forecastRevenue", system: "Prediction Engine", status: "Success", durationMs: 211, resultSize: "6 periods" },
    { toolName: "generateRecommendation", system: "Recommendation Engine", status: "Success", durationMs: 297, resultSize: "2 recommendations" }
  ];
}

export function getLearningLoop(): LearningLoopItem[] {
  return [
    {
      recommendationId: "REC-001",
      action: "Accepted",
      outcome: "Meeting scheduled with Parker Family Trust.",
      learningSignal: "Positive engagement signal increased recommendation confidence.",
      memoryUpdate: "Stored as long-term advisor strategy memory."
    },
    {
      recommendationId: "REC-002",
      action: "Modified",
      outcome: "Advisor adjusted outreach timing.",
      learningSignal: "Timing preference captured for future actions.",
      memoryUpdate: "Stored as episodic feedback memory."
    }
  ];
}
