"use client";

import { useEffect, useState } from "react";
import { Database, DollarSign, PiggyBank, TrendingUp } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { fetchAdvisor360Integrated } from "@/lib/api/integrated-expanded";
import { AgentTraceStrip } from "@/components/integrated/common/agent-trace-strip";
import { StatusPill } from "@/components/integrated/common/status-pill";
import { KpiCard } from "@/components/cards/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";

export function Advisor360Client() {
  const context = useApiContextPayload();
  const [data, setData] = useState<any | null>(null);

  useEffect(() => {
    setData(null);
    fetchAdvisor360Integrated(context).then(setData);
  }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  if (!data) return <div className="h-[600px] animate-pulse rounded-xl bg-muted" />;

  const a = data.advisor;
  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <Badge variant="glass">Advisor 360 / Client 360</Badge>
          <h2 className="mt-2 text-[22px] font-black">{a.name}</h2>
          <p className="text-[12px] text-muted-foreground">{a.advisor_id} · {a.market} · persona-aware data refreshed from backend</p>
        </div>
        <StatusPill status={a.agp_status} />
      </div>

      <div className="grid gap-2 md:grid-cols-4">
        <KpiCard label="Revenue YTD" value={formatCurrency(a.revenue_ytd)} change="+12.6%" icon={DollarSign} />
        <KpiCard label="AUM" value={formatCurrency(a.aum)} change="+9.7%" icon={PiggyBank} variant="insight" />
        <KpiCard label="NNM" value={formatCurrency(a.nnm)} change="+5.2%" icon={TrendingUp} />
        <KpiCard label="NCF" value={formatCurrency(a.ncf)} change="+4.2%" icon={Database} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.1fr_.9fr]">
        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Household Intelligence</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data.households.map((h: any) => (
              <div key={h.id} className={h.status === "bad" ? "compact-card compact-card-pad bg-bad-soft" : "compact-card compact-card-pad bg-good-soft"}>
                <div className="flex items-center justify-between"><strong>{h.name}</strong><StatusPill status={h.status} /></div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-[12px]">
                  <div>AUM<br/><strong>{formatCurrency(h.aum)}</strong></div>
                  <div>NNM<br/><strong>{formatCurrency(h.nnm)}</strong></div>
                  <div>Action<br/><strong>{h.next_action}</strong></div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">CRM Activity</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data.crm.map((c: any) => (
              <div key={`${c.date}-${c.subject}`} className="compact-card compact-card-pad">
                <div className="flex items-center justify-between"><strong>{c.subject}</strong><Badge variant="glass">{c.type}</Badge></div>
                <div className="text-[12px] text-muted-foreground">{c.date} · {c.status}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Agent Trace</CardTitle></CardHeader><CardContent className="p-3"><AgentTraceStrip trace={data.agent_trace} /></CardContent></Card>
    </div>
  );
}
