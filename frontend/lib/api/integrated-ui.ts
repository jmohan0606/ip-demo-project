import { apiClient } from "@/lib/api/client";

export type UiContextPayload = {
  persona: string;
  scope_type: string;
  scope_id: string;
  period: string;
  compare_to: string;
};

export async function fetchIntegratedDashboard(context: UiContextPayload) {
  return apiClient.post<any>("/ui-integrated/dashboard", context);
}
export async function fetchIntegratedPageData(pageId: string, context: UiContextPayload) {
  return apiClient.post<any>(`/ui-integrated/page-data/${pageId}`, context);
}
export async function generateIntegratedRecommendations(context: UiContextPayload) {
  return apiClient.post<any>("/ui-integrated/recommendations/generate", context);
}
export async function submitRecommendationFeedback(context: UiContextPayload, recommendation_id: string, action: "accept" | "reject" | "ignore" | "modify" | "complete", notes?: string) {
  return apiClient.post<any>("/ui-integrated/recommendations/feedback", { ...context, recommendation_id, action, notes });
}
export async function ingestKnowledgeDocument(context: UiContextPayload, document_name: string, document_type: string, content: string) {
  return apiClient.post<any>("/ui-integrated/documents/ingest", { ...context, document_name, document_type, content });
}
