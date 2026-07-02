"use client";

import { useEffect, useState } from "react";
import { BrainCircuit, Database, FileText, RefreshCcw, Save } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { buildContextPacketRuntime, fetchMemoryRuntimeStatus, retrieveMemoryRuntime, writeMemoryRuntime } from "@/lib/api/memory-runtime";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function MemoryRuntimeWorkspace() {
  const context = useApiContextPayload();
  const [status, setStatus] = useState<any | null>(null);
  const [query, setQuery] = useState("Why did revenue decline and what should I do next?");
  const [retrieved, setRetrieved] = useState<any | null>(null);
  const [packet, setPacket] = useState<any | null>(null);
  const [writeResult, setWriteResult] = useState<any | null>(null);

  async function refresh() {
    setStatus(await fetchMemoryRuntimeStatus());
    setRetrieved(await retrieveMemoryRuntime(context, query));
    setPacket(await buildContextPacketRuntime(context, query, 900));
  }

  async function writeDemoMemory() {
    setWriteResult(await writeMemoryRuntime(context, {
      memory_type: "Episodic",
      title: "Advisor reviewed managed account opportunity",
      content: "Advisor accepted the managed account review recommendation and wants household-level action steps.",
      importance: 0.91,
      tags: ["recommendation", "managed", "accepted"]
    }));
    await refresh();
  }

  useEffect(() => { refresh(); }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <Badge variant="glass">Memory & Context Platform</Badge>
          <h2 className="mt-2 text-[22px] font-black">Episodic, Semantic, Reasoning Memory & Context Engineering</h2>
          <p className="text-[12px] text-muted-foreground">Retrieves, ranks, prunes and compresses memory + knowledge + graph evidence into context packets.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="h-8 gap-2 text-[12px]" onClick={writeDemoMemory}><Save className="h-4 w-4" />Write Memory</Button>
          <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={refresh}><RefreshCcw className="h-4 w-4" />Refresh</Button>
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <Card className="bg-ai-soft">
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Database className="h-4 w-4" />Runtime Status</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3 text-[12px]">
            <div>Backend: <strong>{status?.memory_backend}</strong></div>
            <div>Memories: <strong>{status?.counts?.memory_events ?? 0}</strong></div>
            <div>Context packets: <strong>{status?.counts?.context_packets ?? 0}</strong></div>
            <div>Graph mode: <strong>{status?.graph_runtime?.active_mode}</strong></div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><BrainCircuit className="h-4 w-4" />Context Query</CardTitle></CardHeader>
          <CardContent className="flex gap-2 p-3">
            <input className="h-9 flex-1 rounded-lg border px-3 text-[12px]" value={query} onChange={(e) => setQuery(e.target.value)} />
            <Button className="h-9 text-[12px]" onClick={refresh}>Build Context</Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 xl:grid-cols-[.9fr_1.1fr]">
        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Retrieved Memories</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {retrieved?.memories?.map((m: any) => (
              <div key={m.memory_id} className="rounded-xl border bg-background p-3 text-[12px]">
                <div className="flex items-center justify-between"><strong>{m.title}</strong><Badge>{m.memory_type}</Badge></div>
                <p className="mt-1 text-muted-foreground">{m.content}</p>
                <div className="mt-2 text-[10px] text-muted-foreground">Score {m.retrieval_score}</div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><FileText className="h-4 w-4" />Context Packet</CardTitle></CardHeader>
          <CardContent className="space-y-3 p-3 text-[12px]">
            {packet && <>
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-xl border bg-good-soft p-2">Tokens<br/><strong>{packet.token_estimate}</strong></div>
                <div className="rounded-xl border bg-ai-soft p-2">Memories<br/><strong>{packet.selected_memories?.length}</strong></div>
                <div className="rounded-xl border bg-warn-soft p-2">Dropped<br/><strong>{packet.pruning_summary?.dropped_items}</strong></div>
              </div>
              <pre className="max-h-[420px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{packet.compressed_context}</pre>
            </>}
          </CardContent>
        </Card>
      </div>

      {writeResult && <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Last Memory Write</CardTitle></CardHeader><CardContent className="p-3"><pre className="max-h-[220px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(writeResult, null, 2)}</pre></CardContent></Card>}
    </div>
  );
}
