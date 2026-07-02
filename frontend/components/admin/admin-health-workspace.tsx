"use client";

import { Database, Network, ShieldCheck, Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/cards/kpi-card";
import { Badge } from "@/components/ui/badge";

export function AdminHealthWorkspace() {
  const checks = [
    "TigerGraph MCP mode / REST fallback / Mock fallback visibility",
    "SQLite feature store and preloaded data readiness",
    "Chroma persistent collection and document index readiness",
    "Data freshness, missing data and validation gaps",
    "Deep hardening, runtime validation and UI route coverage"
  ];

  return (
    <div className="animate-slide-up space-y-6">
      <div>
        <Badge variant="glass">Admin / Data Quality / Runtime Health</Badge>
        <h2 className="mt-3 text-3xl font-black tracking-tight">Platform Readiness & Data Quality</h2>
        <p className="mt-2 text-muted-foreground">Runtime health, data freshness, graph mode, Chroma, SQLite and readiness checks.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Data Quality" value="96%" change="+2.4%" icon={Database} variant="insight" />
        <KpiCard label="Graph Mode" value="Mock" change="MCP pending" icon={Network} variant="risk" />
        <KpiCard label="UI Routes" value="16/16" change="Ready" icon={ShieldCheck} />
        <KpiCard label="Hardening" value="Passed" change="0 gaps" icon={Sparkles} variant="insight" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Readiness Checklist</CardTitle>
          <CardDescription>Final enterprise UI and backend integration checks.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {checks.map((check) => (
            <div key={check} className="rounded-2xl border border-border/70 bg-background/70 p-4">
              <Badge variant="success">Ready</Badge>
              <span className="ml-3 text-sm text-muted-foreground">{check}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
