import { apiClient } from "@/lib/api/client";
import type { UiContextPayload } from "@/lib/api/integrated-ui";

export async function runOrchestration(
  workflow: string,
  context: UiContextPayload,
  inputPayload: Record<string, any> = {}
) {
  return apiClient.post<any>("/orchestration/run", {
    workflow,
    persona: context.persona,
    scope_type: context.scope_type,
    scope_id: context.scope_id,
    period: context.period,
    compare_to: context.compare_to,
    input_payload: inputPayload
  });
}
