import { apiClient } from "@/lib/api/client";
import type { UiContextPayload } from "@/lib/api/integrated-ui";

export async function fetchMemoryRuntimeStatus() {
  return apiClient.get<any>("/memory-runtime/status");
}
export async function writeMemoryRuntime(context: UiContextPayload, payload: Record<string, any>) {
  return apiClient.post<any>("/memory-runtime/write", { ...context, ...payload });
}
export async function retrieveMemoryRuntime(context: UiContextPayload, query: string) {
  return apiClient.post<any>("/memory-runtime/retrieve", { ...context, query });
}
export async function buildContextPacketRuntime(context: UiContextPayload, query: string, max_tokens = 900) {
  return apiClient.post<any>("/memory-runtime/context", { ...context, query, max_tokens });
}
