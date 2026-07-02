import { apiClient } from "@/lib/api/client";

export async function fetchGraphRuntimeStatus() {
  return apiClient.get<any>("/graph-runtime/status");
}

export async function runGraphRuntimeQuery(query_name = "get_advisor_context", params: Record<string, any> = {}) {
  return apiClient.post<any>("/graph-runtime/query", { query_name, params });
}

export async function persistGraphFeedback(recommendation_id: string, action: string, notes = "") {
  return apiClient.post<any>("/graph-runtime/feedback", { recommendation_id, action, notes });
}
