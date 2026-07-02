"use client";

import { useEffect, useState } from "react";
import { BookOpenCheck, Search } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { searchKnowledgeIntegrated } from "@/lib/api/integrated-expanded";
import { AgentTraceStrip } from "@/components/integrated/common/agent-trace-strip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function KnowledgeWorkspace() {
  const context = useApiContextPayload();
  const [query, setQuery] = useState("managed account growth playbook");
  const [data, setData] = useState<any | null>(null);

  async function runSearch(q = query) {
    setData(null);
    setData(await searchKnowledgeIntegrated(context, q));
  }

  useEffect(() => { runSearch(query); }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  return (
    <div className="space-y-3">
      <div><Badge variant="glass">Knowledge / Playbooks / Compliance</Badge><h2 className="mt-2 text-[22px] font-black">Chroma Knowledge Search & Evidence</h2></div>
      <Card>
        <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Search className="h-4 w-4" />Search Knowledge Base</CardTitle></CardHeader>
        <CardContent className="flex gap-2 p-3">
          <input className="h-9 flex-1 rounded-lg border px-3 text-[12px]" value={query} onChange={(e) => setQuery(e.target.value)} />
          <Button className="h-9 gap-1 text-[12px]" onClick={() => runSearch()}><Search className="h-4 w-4" />Search</Button>
        </CardContent>
      </Card>
      {!data ? <div className="h-[300px] animate-pulse rounded-xl bg-muted" /> : (
        <>
          <Card>
            <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><BookOpenCheck className="h-4 w-4" />Results from {data.collection}</CardTitle></CardHeader>
            <CardContent className="space-y-2 p-3">
              {data.results.map((r: any) => <div key={r.title} className="compact-card compact-card-pad"><div className="flex items-center justify-between"><strong>{r.title}</strong><Badge>{Math.round(r.score * 100)}%</Badge></div><p className="mt-1 text-[12px] text-muted-foreground">{r.snippet}</p></div>)}
            </CardContent>
          </Card>
          <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Agent Trace</CardTitle></CardHeader><CardContent className="p-3"><AgentTraceStrip trace={data.agent_trace} /></CardContent></Card>
        </>
      )}
    </div>
  );
}
