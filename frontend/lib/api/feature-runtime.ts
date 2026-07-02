import { apiClient } from "@/lib/api/client";
import type { UiContextPayload } from "@/lib/api/integrated-ui";

export async function fetchFeatureRuntimeStatus() {
  return apiClient.get<any>("/feature-runtime/status");
}
export async function fetchFeatureVector(context: UiContextPayload) {
  return apiClient.post<any>("/feature-runtime/features", context);
}
export async function fetchSimilarity(context: UiContextPayload) {
  return apiClient.post<any>("/feature-runtime/similarity", context);
}
export async function runPrediction(context: UiContextPayload, scenario: Record<string, any> = {}) {
  return apiClient.post<any>("/feature-runtime/predict", { ...context, scenario });
}
