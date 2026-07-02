"use client";

import { useEffect, useState } from "react";
import { BrainCircuit, Clock, FileSearch } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { fetchMemoryExplainabilityIntegrated } from "@/lib/api/integrated-expanded";
import { AgentTraceStrip } from "@/components/integrated/common/agent-trace-strip";
import { StatusPill } from "@/components/integrated/common/status-pill";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function MemoryExplainabilityWorkspace() {
  const context = useApiContextPayload();
  const [data, setData] = useState<any | null>(null);

  useEffect(() => {
    setData(null);
    fetchMemoryExplainabilityIntegrated(context).then(setData);
  }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  if (!data) return <div className="h-[600px] animate-pulse rounded-xl bg-muted" />;

  return (
    <div className="space-y-3">
      <div><Badge variant="glass">Memory Timeline & Explainability</Badge><h2 className="mt-2 text-[22px] font-black">Memory, Evidence & Reasoning Trace</h2></div>
      <div className="grid gap-3 xl:grid-cols-[.95fr_1.05fr]">
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Clock className="h-4 w-4" />Memory Timeline</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data.timeline.map((t: any) => <div key={`${t.date}-${t.title}`} className="compact-card compact-card-pad"><div className="flex items-center justify-between"><strong>{t.title}</strong><StatusPill status={t.status} /></div><div className="text-[12px] text-muted-foreground">{t.date} · {t.type}</div></div>)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><BrainCircuit className="h-4 w-4" />Explainability Path</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data.explainability_path.map((step: string, index: number) => <div key={step} className="rounded-xl border bg-ai-soft p-3 text-[12px]"><strong>{index + 1}. {step}</strong></div>)}
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><FileSearch className="h-4 w-4" />Evidence</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data.evidence.map((e: any) => <div key={`${e.source}-${e.item}`} className="compact-card compact-card-pad"><strong>{e.source}</strong><div className="text-[12px] text-muted-foreground">{e.item}</div></div>)}
          </CardContent>
        </Card>
        <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Agent Trace</CardTitle></CardHeader><CardContent className="p-3"><AgentTraceStrip trace={data.agent_trace} /></CardContent></Card>
      </div>
    </div>
  );
}
