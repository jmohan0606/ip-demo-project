import { apiClient } from "@/lib/api/client";
import type { UiContextPayload } from "@/lib/api/integrated-ui";

export async function fetchLlmActivationStatus() {
  return apiClient.get<any>("/llm-activation/status");
}

export async function askActivatedAssistant(context: UiContextPayload, question: string) {
  return apiClient.post<any>("/llm-activation/ask", { ...context, question });
}

export async function generateRecommendationNarrative(context: UiContextPayload) {
  return apiClient.post<any>("/llm-activation/recommendation-narrative", { ...context });
}
