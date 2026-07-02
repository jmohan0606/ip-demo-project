import { apiClient } from "@/lib/api/client";

export async function fetchTigerGraphActivationStatus() {
  return apiClient.get<any>("/tigergraph-activation/status");
}

export async function runTigerGraphLogicalQuery(logical_name: string, params: Record<string, any>) {
  return apiClient.post<any>("/tigergraph-activation/query", { logical_name, params });
}

export async function runTigerGraphActivationSmokeTest() {
  return apiClient.post<any>("/tigergraph-activation/smoke-test", {});
}
