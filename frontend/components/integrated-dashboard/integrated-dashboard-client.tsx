"use client";

import { useEffect, useState } from "react";
import { Bot, BrainCircuit, CheckCircle2, Sparkles } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { fetchIntegratedDashboard, submitRecommendationFeedback } from "@/lib/api/integrated-ui";
import { CompactKpiCard } from "@/components/integrated-dashboard/compact-kpi-card";
import { MiniLineChart } from "@/components/integrated-dashboard/mini-line-chart";
import { ProductDonut } from "@/components/integrated-dashboard/product-donut";
import { ActionButton } from "@/components/integrated-dashboard/action-button";
import { DashboardDetailDrawer } from "@/components/integrated-dashboard/dashboard-detail-drawer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function IntegratedDashboardClient() {
  const context = useApiContextPayload();
  const [data, setData] = useState<any | null>(null);
  const [drawer, setDrawer] = useState<{ title: string; body: any } | null>(null);
  const [chatOpen, setChatOpen] = useState(true);

  useEffect(() => {
    setData(null);
    fetchIntegratedDashboard(context).then(setData);
  }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  if (!data) return <div className="h-[600px] animate-pulse rounded-xl bg-muted" />;

  return (
    <div className="grid gap-3 xl:grid-cols-[1fr_310px]">
      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-6">
          {data.kpis.map((item: any) => <button key={item.label} onClick={() => setDrawer({ title: item.label, body: item })} className="text-left"><CompactKpiCard item={item} /></button>)}
        </div>

        <div className="grid gap-3 xl:grid-cols-2">
          <Card className="bg-ai-soft">
            <CardHeader className="p-3 pb-1"><CardTitle className="flex items-center gap-2 text-[13px]"><Sparkles className="h-4 w-4 text-indigo-600" />AI Insight Summary</CardTitle></CardHeader>
            <CardContent className="p-3">
              <h3 className="font-black">{data.insight_summary.title}</h3>
              <p className="mt-2 text-[12px] leading-5 text-muted-foreground">{data.insight_summary.body}</p>
              <div className="mt-3 grid gap-2 md:grid-cols-3">
                {data.insight_summary.drivers.map((d: any) => (
                  <div key={d.label} className={d.status === "bad" ? "compact-card compact-card-pad bg-bad-soft" : "compact-card compact-card-pad bg-good-soft"}>
                    <div className="text-[11px] font-bold">{d.label}</div><div className={d.status === "bad" ? "status-bad" : "status-good"}>{d.value}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-good-soft">
            <CardHeader className="p-3 pb-1"><CardTitle className="flex items-center gap-2 text-[13px]"><Bot className="h-4 w-4 text-green-600" />AI Coaching Card</CardTitle></CardHeader>
            <CardContent className="grid gap-2 p-3 text-[12px]">
              <div className="compact-card compact-card-pad"><strong>Recommendation:</strong> {data.coaching_card.recommendation}</div>
              <div className="compact-card compact-card-pad"><strong>Shoutout:</strong> {data.coaching_card.shoutout}</div>
              <div className="compact-card compact-card-pad"><strong>Action Steps:</strong><ul className="mt-1 list-disc pl-4">{data.coaching_card.actions.map((a: string) => <li key={a}>{a}</li>)}</ul></div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-3 xl:grid-cols-[1fr_1fr_.85fr_.85fr]">
          <Card><CardHeader className="p-3 pb-1"><CardTitle className="text-[13px]">Revenue Trend</CardTitle></CardHeader><CardContent className="p-3"><MiniLineChart data={data.series} /></CardContent></Card>
          <Card><CardHeader className="p-3 pb-1"><CardTitle className="text-[13px]">Revenue by Product Category</CardTitle></CardHeader><CardContent className="p-3"><ProductDonut data={data.product_mix} /></CardContent></Card>
          <Card><CardHeader className="p-3 pb-1"><CardTitle className="text-[13px]">Top Opportunities</CardTitle></CardHeader><CardContent className="space-y-2 p-3">{data.opportunities.map((o: any) => <div key={o.name} className="flex items-center justify-between rounded-lg border p-2 text-[11px]"><span>{o.name}</span><Badge variant={o.priority === "High" ? "destructive" : "warning"}>{o.score}</Badge></div>)}</CardContent></Card>
          <Card><CardHeader className="p-3 pb-1"><CardTitle className="text-[13px]">Top Recommendations</CardTitle></CardHeader><CardContent className="space-y-2 p-3">{data.recommendations.map((r: any) => <div key={r.id} className="rounded-lg border p-2 text-[11px]"><div className="flex items-center justify-between"><span>{r.name}</span><Badge variant="glass">{r.score}</Badge></div><div className="mt-2 flex gap-1"><ActionButton action="accept" onClick={() => submitRecommendationFeedback(context, r.id, "accept")} /><ActionButton action="reject" onClick={() => submitRecommendationFeedback(context, r.id, "reject")} /><ActionButton action="ignore" onClick={() => submitRecommendationFeedback(context, r.id, "ignore")} /></div></div>)}</CardContent></Card>
        </div>

        <Card><CardHeader className="p-3 pb-1"><CardTitle className="flex items-center gap-2 text-[13px]"><BrainCircuit className="h-4 w-4 text-indigo-600" />System Trace</CardTitle></CardHeader><CardContent className="flex flex-wrap gap-2 p-3">{data.agent_trace.agents.map((a: any) => <Badge key={a.agent_name} variant="success" className="gap-1"><CheckCircle2 className="h-3 w-3" />{a.agent_name}</Badge>)}</CardContent></Card>
      </div>

      {chatOpen ? (
        <aside className="rounded-xl border bg-card p-3 shadow-sm">
          <div className="flex items-center justify-between"><h3 className="font-black">AI Chat Assistant</h3><button onClick={() => setChatOpen(false)} className="text-[11px] text-muted-foreground">Collapse</button></div>
          <div className="mt-3 space-y-3 text-[12px]">
            <div className="rounded-xl bg-muted p-3">Hi, how can I help you today?</div>
            <div className="rounded-xl bg-blue-600 p-3 text-white">Why is my revenue down in the Downtown market?</div>
            <div className="rounded-xl border bg-good-soft p-3">Revenue pressure is tied to Fixed Income redemptions, but managed account growth is offsetting part of the decline.</div>
            <button className="w-full rounded-lg bg-blue-600 px-3 py-2 text-white">Show me opportunities</button>
          </div>
        </aside>
      ) : <button onClick={() => setChatOpen(true)} className="fixed right-4 top-24 z-40 rounded-full bg-blue-600 px-3 py-2 text-white shadow-lg">AI Chat</button>}

      <DashboardDetailDrawer title={drawer?.title ?? ""} open={!!drawer} onClose={() => setDrawer(null)}>
        <pre className="rounded-xl bg-muted p-3 text-[11px]">{JSON.stringify(drawer?.body, null, 2)}</pre>
      </DashboardDetailDrawer>
    </div>
  );
}
