import { apiClient } from "@/lib/api/client";
import type { UiContextPayload } from "@/lib/api/integrated-ui";

export async function fetchAdvisor360Integrated(context: UiContextPayload) {
  return apiClient.post<any>("/ui-integrated/advisor-360", context);
}
export async function fetchRecommendationsWorkspace(context: UiContextPayload) {
  return apiClient.post<any>("/ui-integrated/recommendations/workspace", context);
}
export async function fetchGraphExplorerIntegrated(context: UiContextPayload) {
  return apiClient.post<any>("/ui-integrated/graph/explore", context);
}
export async function fetchFeaturesEmbeddingsIntegrated(context: UiContextPayload) {
  return apiClient.post<any>("/ui-integrated/features-embeddings", context);
}
export async function fetchMemoryExplainabilityIntegrated(context: UiContextPayload) {
  return apiClient.post<any>("/ui-integrated/memory-explainability", context);
}
export async function searchKnowledgeIntegrated(context: UiContextPayload, query: string) {
  return apiClient.post<any>("/ui-integrated/knowledge/search", { ...context, query });
}
