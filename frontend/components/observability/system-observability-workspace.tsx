"use client";

import { Activity, AlertTriangle, BarChart3, Bot, Database, Gauge, Network, ShieldCheck } from "lucide-react";
import {
  getAgentMetrics,
  getCostMetrics,
  getErrorEvents,
  getServiceHealth,
  getWorkflowTraces
} from "@/lib/api/observability";
import { AgentMetricsTable } from "@/components/observability/agent-metrics-table";
import { ErrorEventsPanel } from "@/components/observability/error-events-panel";
import { ServiceHealthGrid } from "@/components/observability/service-health-grid";
import { WorkflowTraceList } from "@/components/observability/workflow-trace-list";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/cards/kpi-card";
import { Badge } from "@/components/ui/badge";

export function SystemObservabilityWorkspace() {
  const services = getServiceHealth();
  const agents = getAgentMetrics();
  const traces = getWorkflowTraces();
  const costs = getCostMetrics();
  const errors = getErrorEvents();

  return (
    <div className="animate-slide-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Badge variant="glass">System Observability & Agent Operations</Badge>
          <h2 className="mt-3 text-3xl font-black tracking-tight">Runtime Health, Agent Ops & Governance</h2>
          <p className="mt-2 max-w-3xl text-muted-foreground">
            Monitor LangGraph agents, MCP/REST/mock graph access, Chroma, feature store, prediction engines, memory, ingestion, API health, costs, errors and audit posture.
          </p>
        </div>
        <Badge variant="warning">MCP Pending · Mock Fallback Active</Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Healthy Services" value="10 / 12" change="+2" icon={ShieldCheck} variant="insight" />
        <KpiCard label="Agent Success Rate" value="98.2%" change="+1.1%" icon={Bot} />
        <KpiCard label="Avg Workflow Latency" value="1.38s" change="-4.2%" icon={Gauge} variant="insight" />
        <KpiCard label="Active Fallback Rate" value="18%" change="MCP pending" icon={AlertTriangle} variant="risk" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Activity className="h-5 w-5 text-primary" /> Service Health Dashboard</CardTitle>
          <CardDescription>Agent, graph, vector, database, model, memory, ingestion and API health.</CardDescription>
        </CardHeader>
        <CardContent>
          <ServiceHealthGrid services={services} />
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_.95fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Bot className="h-5 w-5 text-primary" /> Agent Operations</CardTitle>
            <CardDescription>Success/failure rates, executions and average latency by agent.</CardDescription>
          </CardHeader>
          <CardContent>
            <AgentMetricsTable rows={agents} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Network className="h-5 w-5 text-primary" /> LangGraph Workflow Traces</CardTitle>
            <CardDescription>End-to-end agent workflows and active graph access mode.</CardDescription>
          </CardHeader>
          <CardContent>
            <WorkflowTraceList traces={traces} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[.85fr_1.15fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><BarChart3 className="h-5 w-5 text-primary" /> Token, Cost & Usage</CardTitle>
            <CardDescription>Demo-level usage visibility for cost governance.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {costs.map((item) => (
              <div key={item.metric} className="flex items-center justify-between rounded-2xl border border-border/70 bg-background/70 p-4">
                <div className="font-bold">{item.metric}</div>
                <div className="text-right">
                  <div className="font-black">{item.value}</div>
                  <div className="text-xs text-muted-foreground">{item.trend}</div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-primary" /> Error Analysis & Remediation</CardTitle>
            <CardDescription>Operational issues, fallback behavior and remediation actions.</CardDescription>
          </CardHeader>
          <CardContent>
            <ErrorEventsPanel events={errors} />
          </CardContent>
        </Card>
      </div>

      <Card className="insight-gradient">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Database className="h-5 w-5 text-primary" /> Audit & Governance Coverage</CardTitle>
          <CardDescription>What this operations page makes visible to architecture reviewers.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm text-muted-foreground md:grid-cols-2">
          <div>Agent health, success rates, latency and failures.</div>
          <div>LangGraph execution traces and route visibility.</div>
          <div>TigerGraph MCP, REST fallback and mock fallback mode awareness.</div>
          <div>Chroma, SQLite feature store, memory and ingestion health.</div>
          <div>Prediction/recommendation service status.</div>
          <div>Token usage, runtime cost, audit events and governance coverage.</div>
        </CardContent>
      </Card>
    </div>
  );
}
