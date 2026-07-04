import { apiClient } from "@/lib/api/client";
import type { ApiEnvelope } from "@/lib/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export interface RagSource {
  chunk_id: string;
  document_id: string;
  document_name: string;
  document_category: string;
  similarity: number | null;
  excerpt: string;
}

export interface RagAnswer {
  question: string;
  found: boolean;
  answer: string;
  sources: RagSource[];
  generated_by: { mode: string; model?: string; reason?: string };
  retrieval: {
    top_k: number;
    min_similarity: number;
    collection_name: string;
    sources_used: number;
  };
}

export interface UploadResult {
  document_id: string;
  document_name: string;
  document_category: string;
  chunks_created: number;
  indexed_count: number;
  collection_name: string;
  status: string;
  message: string;
}

export interface CatalogDocument {
  document_id: string;
  document_name: string;
  document_category?: string;
  document_type?: string;
  status?: string;
  [key: string]: unknown;
}

/** Full RAG: retrieve top-k semantic chunks -> grounded prompt -> LLM -> cited answer. */
export function askKnowledge(question: string, topK = 5): Promise<RagAnswer> {
  return apiClient.post<RagAnswer>("/knowledge/ask", { query: question, top_k: topK });
}

export function listKnowledgeDocuments(): Promise<CatalogDocument[]> {
  return apiClient.get<CatalogDocument[]>("/knowledge/documents");
}

/** Real ingestion of an uploaded file (multipart) through parse -> chunk -> embed -> Chroma. */
export async function uploadKnowledgeDocument(
  file: File,
  category?: string,
): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  if (category) form.append("document_category", category);
  const response = await fetch(`${API_BASE_URL}/knowledge/upload`, {
    method: "POST",
    body: form,
    cache: "no-store",
  });
  const payload = (await response.json()) as ApiEnvelope<UploadResult>;
  if (!response.ok || !payload.success) {
    throw new Error(payload.message || payload.error || `Upload failed (${response.status})`);
  }
  return payload.data;
}
