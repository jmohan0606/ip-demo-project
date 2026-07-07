"use client";

import { useEffect, useState } from "react";
import { Waypoints, ArrowRight, Brain, History } from "lucide-react";

import { apiClient } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { colors } from "@/styles/tokens";

interface Hop { hop: number; edge: string; from: unknown; to: unknown; description: string }
interface Prior { reasoning_id: string; created_at?: string; conclusion?: string }
interface GraphReasoning {
  path: Hop[];
  prior_reasoning: Prior[];
  traversal?: { similar_advisors?: Array<{ name: string; similarity_score: number }>;
                peer_success_patterns?: Array<{ family: string; proven: number; total_impact: number }>;
                top_contributors?: Array<{ name: string; open_opportunities: number }> };
}

/**
 * Item 3 — makes the graph reasoning VISIBLE: the real multi-hop traversal path
 * (entities visited + relationships walked) and the prior reasoning traces reused,
 * from GET /explainability/graph-reasoning. This is the actual walk the answer was
 * grounded in — not a narrated path.
 */
export function GraphReasoningPath({ scopeType = "ADVISOR", scopeId }: { scopeType?: string; scopeId: string }) {
  const [data, setData] = useState<GraphReasoning | null>(null);
  useEffect(() => {
    if (!scopeId) return;
    apiClient
      .get<GraphReasoning>(`/explainability/graph-reasoning/${scopeType}/${scopeId}`)
      .then(setData)
      .catch(() => setData(null));
  }, [scopeType, scopeId]);

  if (!data || !data.path?.length) return null;
  const t = data.traversal ?? {};
  return (
    <Card data-story-target="graph-reasoning-path">
      <CardHeader className="flex flex-row items-center justify-between p-3">
        <CardTitle className="flex items-center gap-2 text-[13px]">
          <Waypoints className="h-4 w-4" style={{ color: colors.aiAccent }} /> Graph Relational Reasoning — traversal path
        </CardTitle>
        <span className="text-[10px] text-muted-foreground">{data.path.length} hops walked · real entities visited</span>
      </CardHeader>
      <CardContent className="space-y-3 p-3">
        {/* the multi-hop path */}
        <ol className="space-y-1.5">
          {data.path.map((h) => (
            <li key={h.hop} className="flex items-start gap-2 rounded-lg border p-2" style={{ borderColor: colors.surface.border }}>
              <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ backgroundColor: colors.aiAccent }}>{h.hop}</span>
              <div className="min-w-0">
                <div className="flex items-center gap-1 font-mono text-[10px]" style={{ color: colors.primary }}>
                  {String(h.edge)} <ArrowRight className="h-3 w-3" />
                </div>
                <div className="text-[12px]" style={{ color: colors.text.primary }}>{h.description}</div>
              </div>
            </li>
          ))}
        </ol>
        {/* what the traversal surfaced */}
        {!!(t.peer_success_patterns?.length) && (
          <div className="rounded-lg p-2 text-[11px]" style={{ background: "#EEF2FF", color: colors.text.secondary }}>
            <span className="font-semibold" style={{ color: colors.aiAccent }}>Peer success (from similar advisors traversed): </span>
            {t.peer_success_patterns.slice(0, 3).map((p) => `${p.family} (proven ${p.proven}×, $${Math.round(p.total_impact).toLocaleString()})`).join(" · ")}
          </div>
        )}
        {!!(t.top_contributors?.length) && (
          <div className="rounded-lg p-2 text-[11px]" style={{ background: "#EEF2FF", color: colors.text.secondary }}>
            <span className="font-semibold" style={{ color: colors.aiAccent }}>Top contributors found by traversal: </span>
            {t.top_contributors.slice(0, 4).map((c) => `${c.name} (${c.open_opportunities} opps)`).join(" · ")}
          </div>
        )}
        {/* prior reasoning reused */}
        <div className="flex items-start gap-2 border-t pt-2" style={{ borderColor: colors.surface.border }}>
          {data.prior_reasoning?.length ? <History className="mt-0.5 h-3.5 w-3.5" style={{ color: colors.positive }} /> : <Brain className="mt-0.5 h-3.5 w-3.5 text-muted-foreground" />}
          <div className="text-[11px]" style={{ color: colors.text.secondary }}>
            {data.prior_reasoning?.length
              ? <>Reused <b>{data.prior_reasoning.length}</b> prior reasoning trace(s) — the agent builds on past conclusions: <i>{data.prior_reasoning[0].conclusion?.slice(0, 90)}</i></>
              : "No prior reasoning traces yet — the next question will build on this answer's recorded trace."}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
