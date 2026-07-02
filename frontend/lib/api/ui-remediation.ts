export type UiContext = { persona?: string; scope_type?: string; scope_id?: string; period?: string; compare_to?: string; };
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
async function post<T>(path: string, payload: any = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  const json = await res.json();
  return json.data ?? json;
}
export const defaultContext: UiContext = { persona: "Executive", scope_type: "Region", scope_id: "REG101", period: "YTD", compare_to: "Prior Year" };
export const uiApi = {
  dashboard: (ctx: UiContext = defaultContext) => post<any>("/ui-remediation/dashboard", ctx),
  revenue: (ctx: UiContext = defaultContext) => post<any>("/ui-remediation/revenue-analytics", ctx),
  advisor: (ctx: UiContext = defaultContext) => post<any>("/ui-remediation/advisor-360", ctx),
  recommendations: (ctx: UiContext = defaultContext) => post<any>("/ui-remediation/recommendations", ctx),
  graph: (ctx: UiContext = defaultContext) => post<any>("/ui-remediation/graph-explorer", ctx),
  features: (ctx: UiContext = defaultContext) => post<any>("/ui-remediation/features-embeddings", ctx),
  memory: (ctx: UiContext = defaultContext) => post<any>("/ui-remediation/memory-explainability", ctx),
  assistant: (question: string, ctx: UiContext = defaultContext) => post<any>("/ui-remediation/assistant", {...ctx, question}),
  ingest: (payload: any) => post<any>("/ui-remediation/document-ingestion", payload),
};
