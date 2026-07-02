export const endpoints = {
  graphHealth: "/graph-access/health",
  finalAudit: "/final-audit/run",
  runtimeValidation: "/runtime-validation/run",
  deepHardening: "/deep-hardening/run",
  agenticRun: "/agentic-ai/run",
  insightsGenerate: "/insights-coaching/generate",
  aiChatAsk: "/ai-chat/ask"
} as const;
