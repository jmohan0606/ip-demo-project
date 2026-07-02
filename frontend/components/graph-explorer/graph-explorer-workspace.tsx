"use client";

import { useEffect, useState } from "react";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import "reactflow/dist/style.css";
import { Network } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { fetchGraphExplorerIntegrated } from "@/lib/api/integrated-expanded";
import { AgentTraceStrip } from "@/components/integrated/common/agent-trace-strip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function GraphExplorerWorkspace() {
  const context = useApiContextPayload();
  const [data, setData] = useState<any | null>(null);
  const [selected, setSelected] = useState<any | null>(null);

  useEffect(() => {
    setData(null);
    fetchGraphExplorerIntegrated(context).then(setData);
  }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  if (!data) return <div className="h-[600px] animate-pulse rounded-xl bg-muted" />;

  const positions = [{x:0,y:140},{x:250,y:40},{x:500,y:40},{x:750,y:40},{x:500,y:240},{x:750,y:240},{x:250,y:300}];
  const nodes = data.nodes.map((n: any, i: number) => ({
    id: n.id,
    position: positions[i] ?? {x:i*120,y:i*50},
    data: { label: `${n.type}: ${n.label}` },
    style: { borderRadius: 12, padding: 10, border: "1px solid rgba(148,163,184,.45)", background: "#0f172a", color: "white", fontSize: 11, fontWeight: 700 }
  }));
  const edges = data.edges.map((e: any, i: number) => ({ id: `e-${i}`, source: e.source, target: e.target, label: e.label, animated: true }));

  return (
    <div className="space-y-3">
      <div><Badge variant="glass">Knowledge Graph Explorer</Badge><h2 className="mt-2 text-[22px] font-black">TigerGraph Relationship Explorer</h2></div>
      <div className="grid gap-3 xl:grid-cols-[1.2fr_.8fr]">
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Network className="h-4 w-4" />Graph Canvas</CardTitle></CardHeader>
          <CardContent className="p-3"><div className="h-[560px] overflow-hidden rounded-xl border bg-slate-950"><ReactFlow nodes={nodes} edges={edges} fitView onNodeClick={(_, node) => setSelected(data.nodes.find((n: any) => n.id === node.id))}><Background /><MiniMap /><Controls /></ReactFlow></div></CardContent>
        </Card>
        <div className="space-y-3">
          <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Selected Node</CardTitle></CardHeader><CardContent className="p-3">{selected ? <div className="compact-card compact-card-pad"><strong>{selected.label}</strong><div className="text-[12px] text-muted-foreground">{selected.id} · {selected.type} · Score {selected.score}</div></div> : <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">Select a node.</div>}</CardContent></Card>
          <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Agent Trace</CardTitle></CardHeader><CardContent className="p-3"><AgentTraceStrip trace={data.agent_trace} /></CardContent></Card>
        </div>
      </div>
    </div>
  );
}
