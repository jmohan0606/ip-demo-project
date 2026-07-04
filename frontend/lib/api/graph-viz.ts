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
  nodes: GraphVizNode[];
  edges: GraphVizEdge[];
  counts: { nodes: number; edges: number };
  evidence: { source: string; edges_traversed: string[] };
}

/** Real one-hop subgraph around an advisor from the foundation graph. */
export async function fetchNeighborhood(advisorId: string): Promise<GraphNeighborhood> {
  return apiClient.get<GraphNeighborhood>(
    `/graph-viz/neighborhood?advisor_id=${encodeURIComponent(advisorId)}`,
  );
}
