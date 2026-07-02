"use client";

import { CheckCircle2, FileUp, RotateCcw, UploadCloud } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/cards/kpi-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function DataIngestionWorkspace() {
  const loads = [
    { file: "phx_dm_advisor.csv", status: "Validated", rows: "30", mode: "MCP-first" },
    { file: "phx_dm_household.csv", status: "Validated", rows: "30+", mode: "MCP-first" },
    { file: "phx_dm_transaction.csv", status: "Validated", rows: "300+", mode: "MCP-first" },
    { file: "phx_dm_net_new_money.csv", status: "Validated", rows: "Derived", mode: "MCP-first" },
    { file: "phx_dm_net_cash_flow.csv", status: "Validated", rows: "Derived", mode: "MCP-first" }
  ];

  return (
    <div className="animate-slide-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Badge variant="glass">Data Ingestion & Sync</Badge>
          <h2 className="mt-3 text-3xl font-black tracking-tight">Upload, Validate, Retry & Resume</h2>
          <p className="mt-2 text-muted-foreground">MCP-first ingestion workflow with validation, progress, checkpointing and retry/resume support.</p>
        </div>
        <Button variant="premium" className="gap-2"><FileUp className="h-4 w-4" /> Upload CSV</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Validated Files" value="18" change="+5" icon={CheckCircle2} variant="insight" />
        <KpiCard label="Rows Ready" value="1.8K" change="+320" icon={UploadCloud} />
        <KpiCard label="Retry Queue" value="0" change="Clear" icon={RotateCcw} variant="insight" />
        <KpiCard label="Checkpoint Status" value="Ready" change="Resume enabled" icon={CheckCircle2} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Load History</CardTitle>
          <CardDescription>Source validation and MCP-first load readiness.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loads.map((load) => (
            <div key={load.file} className="grid gap-3 rounded-2xl border border-border/70 bg-background/70 p-4 md:grid-cols-4 md:items-center">
              <div className="font-bold">{load.file}</div>
              <Badge variant="success">{load.status}</Badge>
              <div className="text-sm text-muted-foreground">{load.rows} rows</div>
              <div className="text-sm text-muted-foreground">{load.mode}</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
