import { apiClient } from "@/lib/api/client";
import type { HierarchyNode } from "@/lib/types/shell";

export function fetchHierarchyTree(): Promise<{ firms: HierarchyNode[] }> {
  return apiClient.get<{ firms: HierarchyNode[] }>("/hierarchy/tree");
}

export interface ScopeResolution {
  scope_type: string;
  scope_id: string;
  advisor_count: number;
  advisor_ids: string[];
}

export function resolveScope(scopeType: string, scopeId: string): Promise<ScopeResolution> {
  return apiClient.get<ScopeResolution>(
    `/hierarchy/resolve?scope_type=${encodeURIComponent(scopeType)}&scope_id=${encodeURIComponent(scopeId)}`,
  );
}
