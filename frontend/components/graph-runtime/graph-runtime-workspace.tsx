"use client";

import { useEffect, useState } from "react";
import { Database, Network, PlayCircle, ShieldCheck } from "lucide-react";
import { fetchGraphRuntimeStatus, persistGraphFeedback, runGraphRuntimeQuery } from "@/lib/api/graph-runtime";
import { ActionButton } from "@/components/integrated-dashboard/action-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function GraphRuntimeWorkspace() {
  const [status, setStatus] = useState<any | null>(null);
  const [query, setQuery] = useState<any | null>(null);
  const [feedback, setFeedback] = useState<any | null>(null);

  async function refresh() {
    setStatus(await fetchGraphRuntimeStatus());
  }

  async function runQuery() {
    setQuery(await runGraphRuntimeQuery("get_advisor_context", { advisor_id: "ADV0001" }));
  }

  useEffect(() => { refresh(); }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <Badge variant="glass">TigerGraph MCP-First Tool Runtime</Badge>
          <h2 className="mt-2 text-[22px] font-black">Graph Runtime & Persistence</h2>
          <p className="text-[12px] text-muted-foreground">MCP → REST → mock fallback with query, vertex, edge and feedback persistence semantics.</p>
        </div>
        <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={refresh}><ShieldCheck className="h-4 w-4" />Refresh Status</Button>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <Card className={status?.active_mode === "mcp" ? "bg-good-soft" : status?.active_mode === "rest" ? "bg-warn-soft" : "bg-ai-soft"}>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Network className="h-4 w-4" />Runtime Status</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3 text-[12px]">
            <div>Active mode: <strong>{status?.active_mode ?? "loading"}</strong></div>
            <div>MCP available: <strong>{String(status?.mcp_available)}</strong></div>
            <div>REST available: <strong>{String(status?.rest_available)}</strong></div>
            <div>Mock available: <strong>{String(status?.mock_available)}</strong></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Database className="h-4 w-4" />Graph Query</CardTitle></CardHeader>
          <CardContent className="space-y-3 p-3">
            <Button className="h-8 gap-2 text-[12px]" onClick={runQuery}><PlayCircle className="h-4 w-4" />Run Advisor Context Query</Button>
            {query && <pre className="max-h-[240px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(query, null, 2)}</pre>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Feedback Persistence</CardTitle></CardHeader>
          <CardContent className="space-y-3 p-3 text-[12px]">
            <div className="flex gap-2">
              <ActionButton action="accept" onClick={async () => setFeedback(await persistGraphFeedback("REC-001", "accept"))} />
              <ActionButton action="reject" onClick={async () => setFeedback(await persistGraphFeedback("REC-001", "reject"))} />
              <ActionButton action="ignore" onClick={async () => setFeedback(await persistGraphFeedback("REC-001", "ignore"))} />
            </div>
            {feedback && <pre className="max-h-[220px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(feedback, null, 2)}</pre>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
