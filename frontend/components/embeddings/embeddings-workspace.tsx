"use client";

import { useEffect, useState } from "react";
import { GitBranch, Search } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { fetchFeaturesEmbeddingsIntegrated } from "@/lib/api/integrated-expanded";
import { AgentTraceStrip } from "@/components/integrated/common/agent-trace-strip";
import { StatusPill } from "@/components/integrated/common/status-pill";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function EmbeddingsWorkspace() {
  const context = useApiContextPayload();
  const [data, setData] = useState<any | null>(null);

  useEffect(() => {
    setData(null);
    fetchFeaturesEmbeddingsIntegrated(context).then(setData);
  }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  if (!data) return <div className="h-[600px] animate-pulse rounded-xl bg-muted" />;

  return (
    <div className="space-y-3">
      <div><Badge variant="glass">Feature Store / Embeddings / Similarity</Badge><h2 className="mt-2 text-[22px] font-black">Feature Vectors, Graph Embeddings & Similarity</h2></div>
      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><GitBranch className="h-4 w-4" />Feature Sets</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data.feature_sets.map((f: any) => <div key={f.name} className="compact-card compact-card-pad"><div className="flex items-center justify-between"><strong>{f.name}</strong><StatusPill status={f.status} /></div><div className="text-[12px] text-muted-foreground">{f.entity} · {f.features} features · freshness {f.freshness}</div></div>)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Search className="h-4 w-4" />Similarity Results</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {data.similar_entities.map((s: any) => <div key={s.entity} className="compact-card compact-card-pad bg-ai-soft"><div className="flex items-center justify-between"><strong>{s.entity}</strong><Badge>{Math.round(s.similarity * 100)}%</Badge></div><div className="text-[12px] text-muted-foreground">{s.reason}</div></div>)}
          </CardContent>
        </Card>
      </div>
      <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Agent Trace</CardTitle></CardHeader><CardContent className="p-3"><AgentTraceStrip trace={data.agent_trace} /></CardContent></Card>
    </div>
  );
}
