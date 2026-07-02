import { apiClient } from "@/lib/api/client";
import type { UiContextPayload } from "@/lib/api/integrated-ui";

export async function fetchRecommendationRuntimeStatus() {
  return apiClient.get<any>("/recommendation-runtime/status");
}
export async function generateRecommendationRuntime(context: UiContextPayload) {
  return apiClient.post<any>("/recommendation-runtime/generate", context);
}
export async function submitRecommendationRuntimeFeedback(recommendation_id: string, action: "accept" | "reject" | "ignore" | "modify" | "complete", notes = "") {
  return apiClient.post<any>("/recommendation-runtime/feedback", { recommendation_id, action, notes });
}
