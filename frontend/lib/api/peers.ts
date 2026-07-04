import { apiClient } from "@/lib/api/client";

export interface PeerDimension {
  metric: string;
  feature: string;
  advisor_percentile: number;
  peer_median_percentile: number;
  advisor_value: number;
  peer_median_value: number;
}

export interface NearestPeer {
  advisor_id: string;
  advisor_name: string;
  similarity_score: number | null;
  reasons: string[];
  revenue_ltm: number;
}

export interface PeerBenchmark {
  advisor_id: string;
  advisor_name: string;
  scope_type: string;
  scope_id: string;
  peer_group_size: number;
  dimensions: PeerDimension[];
  nearest_peers: NearestPeer[];
  evidence: { source: string; peer_ids_resolved: number };
}

export async function fetchPeerBenchmark(
  advisorId: string,
  scopeType: string,
  scopeId: string,
): Promise<PeerBenchmark> {
  return apiClient.get<PeerBenchmark>(
    `/peers/benchmark?advisor_id=${encodeURIComponent(advisorId)}&scope_type=${encodeURIComponent(scopeType)}&scope_id=${encodeURIComponent(scopeId)}`,
  );
}
