"use client";

import { useEffect, useState } from "react";
import { ShieldCheck, Sparkles } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { fetchRecommendationsWorkspace } from "@/lib/api/integrated-expanded";
import { submitRecommendationFeedback } from "@/lib/api/integrated-ui";
import { ActionButton } from "@/components/integrated-dashboard/action-button";
import { AgentTraceStrip } from "@/components/integrated/common/agent-trace-strip";
import { StatusPill } from "@/components/integrated/common/status-pill";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function OpportunitiesRecommendationsWorkspace() {
  const context = useApiContextPayload();
  const [data, setData] = useState<any | null>(null);
  const [selected, setSelected] = useState<any | null>(null);

  useEffect(() => {
    setData(null);
    fetchRecommendationsWorkspace(context).then((r) => { setData(r); setSelected(r.recommendations?.[0]); });
  }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  if (!data) return <div className="h-[600px] animate-pulse rounded-xl bg-muted" />;

  return (
    <div className="space-y-3">
      <div><Badge variant="glass">Opportunities & Recommendations</Badge><h2 className="mt-2 text-[22px] font-black">Next Best Action Workspace</h2></div>
      <div className="grid gap-3 xl:grid-cols-[.85fr_1.15fr]">
        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Opportunity Pipeline</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data.opportunities.map((o: any) => <div key={o.id} className={o.status === "warn" ? "compact-card compact-card-pad bg-warn-soft" : "compact-card compact-card-pad bg-good-soft"}><div className="flex items-center justify-between"><strong>{o.title}</strong><Badge>{o.score}</Badge></div></div>)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Sparkles className="h-4 w-4 text-indigo-600" />Recommendation Queue</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data.recommendations.map((r: any) => (
              <button key={r.id} onClick={() => setSelected(r)} className="w-full compact-card compact-card-pad text-left hover:bg-muted/60">
                <div className="flex items-center justify-between"><strong>{r.title}</strong><StatusPill status={r.compliance} /></div>
                <div className="mt-1 text-[12px] text-muted-foreground">{r.priority} · Confidence {r.confidence}% · Impact {r.impact}</div>
              </button>
            ))}
            {selected && <div className="rounded-xl border bg-ai-soft p-3 text-[12px]">
              <div className="flex items-center gap-2 font-black"><ShieldCheck className="h-4 w-4" />Selected: {selected.title}</div>
              <div className="mt-2 flex flex-wrap gap-2">
                <ActionButton action="accept" onClick={() => submitRecommendationFeedback(context, selected.id, "accept")} />
                <ActionButton action="reject" onClick={() => submitRecommendationFeedback(context, selected.id, "reject")} />
                <ActionButton action="ignore" onClick={() => submitRecommendationFeedback(context, selected.id, "ignore")} />
                <ActionButton action="modify" onClick={() => submitRecommendationFeedback(context, selected.id, "modify")} />
              </div>
            </div>}
          </CardContent>
        </Card>
      </div>
      <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Agent Trace</CardTitle></CardHeader><CardContent className="p-3"><AgentTraceStrip trace={data.agent_trace} /></CardContent></Card>
    </div>
  );
}
