import { apiClient } from "@/lib/api/client";

export interface GraphVizNode {
  id: string;
  type: string;
  group: string;
  label: string;
  attributes: Record<string, unknown>;
}

export interface GraphVizEdge {
  source: string;
  target: string;
  label: string;
}

export interface GraphNeighborhood {
  focal_advisor: { id: string; label: string };
  as_of?: string | null;
  nodes: GraphVizNode[];
  edges: GraphVizEdge[];
  counts: { nodes: number; edges: number; hidden_by_as_of?: number };
  evidence: { source: string; edges_traversed: string[] };
}

/** Real one-hop subgraph around an advisor from the foundation graph. `asOf` (YYYY-MM-DD)
 * requests a point-in-time traversal (Section 11.4). */
export async function fetchNeighborhood(advisorId: string, asOf?: string | null): Promise<GraphNeighborhood> {
  const q = `/graph-viz/neighborhood?advisor_id=${encodeURIComponent(advisorId)}`
    + (asOf ? `&as_of=${asOf}` : "");
  return apiClient.get<GraphNeighborhood>(q);
}
