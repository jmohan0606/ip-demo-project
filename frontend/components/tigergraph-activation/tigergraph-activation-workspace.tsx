"use client";

import { useEffect, useState } from "react";
import { Database, Network, PlayCircle, ShieldCheck } from "lucide-react";
import {
  fetchTigerGraphActivationStatus,
  runTigerGraphActivationSmokeTest,
  runTigerGraphLogicalQuery
} from "@/lib/api/tigergraph-activation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function TigerGraphActivationWorkspace() {
  const [status, setStatus] = useState<any | null>(null);
  const [smoke, setSmoke] = useState<any | null>(null);
  const [query, setQuery] = useState<any | null>(null);

  async function refresh() {
    setStatus(await fetchTigerGraphActivationStatus());
  }

  async function runSmoke() {
    setSmoke(await runTigerGraphActivationSmokeTest());
  }

  async function runAdvisorContext() {
    setQuery(await runTigerGraphLogicalQuery("advisor_context", { advisor_id: "ADV0001" }));
  }

  useEffect(() => { refresh(); }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <Badge variant="glass">Real TigerGraph MCP Integration</Badge>
          <h2 className="mt-2 text-[22px] font-black">Production Data Activation</h2>
          <p className="text-[12px] text-muted-foreground">
            Validates MCP-first runtime, query contracts, REST fallback, and mock fallback before production data cutover.
          </p>
        </div>
        <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={refresh}>
          <ShieldCheck className="h-4 w-4" />Refresh
        </Button>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <Card className={status?.production_data_activation ? "bg-good-soft" : "bg-warn-soft"}>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Network className="h-4 w-4" />Activation Status</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3 text-[12px]">
            <div>Active mode: <strong>{status?.active_mode ?? "loading"}</strong></div>
            <div>MCP available: <strong>{String(status?.mcp_available)}</strong></div>
            <div>REST available: <strong>{String(status?.rest_available)}</strong></div>
            <div>Production data active: <strong>{String(status?.production_data_activation)}</strong></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Database className="h-4 w-4" />Query Contracts</CardTitle></CardHeader>
          <CardContent className="max-h-[260px] space-y-2 overflow-auto p-3 text-[12px]">
            {(status?.contracts ?? []).map((contract: any) => (
              <div key={contract.logical_name} className="rounded-xl border bg-background p-2">
                <strong>{contract.logical_name}</strong>
                <div className="text-muted-foreground">MCP: {contract.mcp_tool_name}</div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Activation Tests</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            <Button className="h-8 w-full gap-2 text-[12px]" onClick={runAdvisorContext}><PlayCircle className="h-4 w-4" />Run Advisor Query</Button>
            <Button variant="outline" className="h-8 w-full gap-2 text-[12px]" onClick={runSmoke}><PlayCircle className="h-4 w-4" />Run Smoke Test</Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Latest Query Result</CardTitle></CardHeader>
          <CardContent className="p-3">
            <pre className="max-h-[420px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(query, null, 2)}</pre>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Smoke Test Result</CardTitle></CardHeader>
          <CardContent className="p-3">
            <pre className="max-h-[420px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(smoke, null, 2)}</pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
