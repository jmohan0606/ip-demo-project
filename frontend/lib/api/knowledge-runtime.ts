import { apiClient } from "@/lib/api/client";

export async function fetchKnowledgeRuntimeStatus() {
  return apiClient.get<any>("/knowledge-runtime/status");
}

export async function searchKnowledgeRuntime(query: string, top_k = 5) {
  return apiClient.post<any>("/knowledge-runtime/search", { query, top_k });
}

export async function ingestKnowledgeRuntime(document_name: string, document_type: string, content: string, metadata: Record<string, any> = {}) {
  return apiClient.post<any>("/knowledge-runtime/ingest", { document_name, document_type, content, metadata });
}
