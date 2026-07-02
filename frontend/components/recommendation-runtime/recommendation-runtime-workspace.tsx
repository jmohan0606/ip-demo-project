"use client";

import { useEffect, useState } from "react";
import { BrainCircuit, RefreshCcw, Sparkles } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { generateRecommendationRuntime, fetchRecommendationRuntimeStatus, submitRecommendationRuntimeFeedback } from "@/lib/api/recommendation-runtime";
import { ActionButton } from "@/components/integrated-dashboard/action-button";
import { StatusPill } from "@/components/integrated/common/status-pill";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";

export function RecommendationRuntimeWorkspace() {
  const context = useApiContextPayload();
  const [status, setStatus] = useState<any | null>(null);
  const [data, setData] = useState<any | null>(null);
  const [feedback, setFeedback] = useState<any | null>(null);
  const [selected, setSelected] = useState<any | null>(null);

  async function refresh() {
    setStatus(await fetchRecommendationRuntimeStatus());
    const result = await generateRecommendationRuntime(context);
    setData(result);
    setSelected(result.recommendations?.[0] ?? null);
  }

  async function act(action: "accept" | "reject" | "ignore" | "modify" | "complete") {
    if (!selected) return;
    setFeedback(await submitRecommendationRuntimeFeedback(selected.recommendation_id, action));
    await refresh();
  }

  useEffect(() => { refresh(); }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <Badge variant="glass">Recommendation & Learning Engine</Badge>
          <h2 className="mt-2 text-[22px] font-black">Opportunities, Next Best Actions & Feedback Learning</h2>
          <p className="text-[12px] text-muted-foreground">Generates opportunities, recommendations, compliance checks, knowledge evidence, and learning signals.</p>
        </div>
        <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={refresh}><RefreshCcw className="h-4 w-4" />Refresh</Button>
      </div>

      <div className="grid gap-3 xl:grid-cols-[.8fr_1.2fr]">
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><BrainCircuit className="h-4 w-4" />Runtime Status</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3 text-[12px]">
            <div>Feedback events: <strong>{status?.learning_store?.feedback_events ?? 0}</strong></div>
            <div>Recommendation states: <strong>{status?.learning_store?.recommendation_states ?? 0}</strong></div>
            <div>Graph active mode: <strong>{status?.graph_runtime?.active_mode}</strong></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Sparkles className="h-4 w-4" />Selected Recommendation</CardTitle></CardHeader>
          <CardContent className="space-y-3 p-3">
            {selected && (
              <div className="rounded-xl border bg-ai-soft p-3 text-[12px]">
                <div className="flex items-center justify-between"><strong>{selected.title}</strong><StatusPill status={selected.compliance_status} /></div>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  <div>Confidence<br/><strong>{Math.round(selected.confidence * 100)}%</strong></div>
                  <div>Impact<br/><strong>{formatCurrency(selected.impact)}</strong></div>
                  <div>Priority<br/><strong>{selected.priority}</strong></div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <ActionButton action="accept" onClick={() => act("accept")} />
                  <ActionButton action="reject" onClick={() => act("reject")} />
                  <ActionButton action="ignore" onClick={() => act("ignore")} />
                  <ActionButton action="modify" onClick={() => act("modify")} />
                </div>
              </div>
            )}
            {feedback && <pre className="max-h-[220px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(feedback, null, 2)}</pre>}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 xl:grid-cols-[.9fr_1.1fr]">
        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Opportunities</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data?.opportunities?.map((o: any) => (
              <div key={o.opportunity_id} className={o.status === "warn" ? "rounded-xl border bg-warn-soft p-3 text-[12px]" : "rounded-xl border bg-good-soft p-3 text-[12px]"}>
                <div className="flex items-center justify-between"><strong>{o.title}</strong><Badge>{Math.round(o.score)}</Badge></div>
                <div className="text-muted-foreground">{o.category} · {formatCurrency(o.impact)} · {o.priority}</div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Recommendation Queue</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data?.recommendations?.map((r: any) => (
              <button key={r.recommendation_id} onClick={() => setSelected(r)} className="w-full rounded-xl border bg-background p-3 text-left text-[12px] hover:bg-muted/60">
                <div className="flex items-center justify-between"><strong>{r.title}</strong><StatusPill status={r.compliance_status} /></div>
                <div className="mt-1 text-muted-foreground">{r.reasoning?.[0]}</div>
                <div className="mt-2 flex gap-2"><Badge>{Math.round(r.confidence * 100)}%</Badge><Badge variant="glass">{formatCurrency(r.impact)}</Badge><Badge variant="secondary">{r.priority}</Badge></div>
              </button>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
