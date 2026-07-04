"use client";
import { useCallback, useEffect, useState } from "react";
import { Bot, PlayCircle, Workflow, ShieldCheck, Network, Brain, Sparkles } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import { runAgenticWorkflow, type AgenticRun } from "@/lib/api/agentic";
import { fetchAdapterStatus, type AdapterStatus } from "@/lib/api/admin";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "glass"> = {
  completed: "success", running: "warning", pending: "glass", failed: "destructive",
};

function durationMs(a: string | null, b: string | null): string {
  if (!a || !b) return "—";
  const ms = new Date(b).getTime() - new Date(a).getTime();
  return Number.isFinite(ms) && ms >= 0 ? `${ms} ms` : "—";
}

export function SystemObservabilityWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [question, setQuestion] = useState("How can this advisor grow revenue?");
  const [run, setRun] = useState<AgenticRun | null>(null);
  const [adapters, setAdapters] = useState<AdapterStatus | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchAdapterStatus().then(setAdapters).catch(() => setAdapters(null));
    apiClient
      .get<{ advisors: Array<{ advisor_id: string; advisor_name: string | null }> }>("/advisor/list")
      .then((r) => setAdvisors(r.advisors))
      .catch(() => setAdvisors([]));
  }, []);

  useEffect(() => {
    if (shell.scopeType === "Advisor") setAdvisorId(shell.scopeId);
    else resolveScope(shell.scopeType, shell.scopeId).then((r) => setAdvisorId(r.advisor_ids[0] ?? "A001")).catch(() => undefined);
  }, [shell.scopeType, shell.scopeId]);

  const execute = useCallback(async () => {
    setBusy(true);
    try {
      setRun(await runAgenticWorkflow(question, advisorId));
    } finally {
      setBusy(false);
    }
  }, [question, advisorId]);

  useEffect(() => {
    void execute();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [advisorId]);

  const services = adapters
    ? [
        { icon: <Network className="h-4 w-4" />, name: "Graph Client", mode: adapters.graph.mode, healthy: adapters.graph.healthy, detail: adapters.graph.graph },
        { icon: <Brain className="h-4 w-4" />, name: "LLM Client", mode: adapters.llm.mode, healthy: true, detail: adapters.llm.model },
        { icon: <Sparkles className="h-4 w-4" />, name: "Embedding Client", mode: adapters.embedding.mode, healthy: true, detail: `${adapters.embedding.model} · ${adapters.embedding.dimensions}d` },
      ]
    : [];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Agent Orchestration &amp; Observability</Badge>
          <h2 className="mt-2 text-[22px] font-black">Live Multi-Agent Workflow Trace</h2>
          <p className="text-[12px] text-muted-foreground">
            Runs the real supervisor→agents orchestration (`/agentic-ai/run`) and shows the actual
            route, per-agent tasks, evidence and confidence — plus live adapter modes. No simulated
            metrics.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="h-8 rounded-lg border border-border bg-background px-2 text-[12px]"
            value={advisorId}
            onChange={(e) => setAdvisorId(e.target.value)}
          >
            {advisors.length === 0 && <option value={advisorId}>{advisorId}</option>}
            {advisors.map((a) => (
              <option key={a.advisor_id} value={a.advisor_id}>{a.advisor_name ?? a.advisor_id}</option>
            ))}
          </select>
          <input
            className="h-8 w-64 rounded-lg border border-border bg-background px-2 text-[12px]"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={execute} disabled={busy}>
            <PlayCircle className="h-4 w-4" /> {busy ? "Running…" : "Run Workflow"}
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Final Agent" value={run ? run.final_agent.replace(/_/g, " ") : "—"} />
        <KpiStatCard label="Confidence" value={run ? `${(run.confidence * 100).toFixed(0)}%` : "—"} />
        <KpiStatCard label="Agent Tasks" value={String(run?.tasks.length ?? "—")} />
        <KpiStatCard label="Evidence Items" value={String(run?.evidence.length ?? "—")} />
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        {services.map((s) => (
          <Card key={s.name}>
            <CardHeader className="flex flex-row items-center justify-between p-3">
              <CardTitle className="flex items-center gap-2 text-[13px]">{s.icon} {s.name}</CardTitle>
              <Badge variant={s.healthy ? "success" : "warning"}>{s.mode}</Badge>
            </CardHeader>
            <CardContent className="p-3 text-[12px] text-muted-foreground">{s.detail}</CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Workflow className="h-4 w-4 text-primary" /> Reasoning Route
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3">
            <ol className="space-y-2">
              {(run?.reasoning_steps ?? []).map((step, i) => (
                <li key={i} className="flex gap-2 text-[12px]">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[10px] font-bold text-primary">
                    {i + 1}
                  </span>
                  <span className="text-muted-foreground">{step}</span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Bot className="h-4 w-4 text-primary" /> Agent Tasks
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="max-h-[280px] overflow-auto">
              <table className="w-full text-[12px]">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2">Agent</th>
                    <th className="px-3 py-2">Instruction</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2 text-right">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {(run?.tasks ?? []).map((t) => (
                    <tr key={t.task_id} className="border-b last:border-0">
                      <td className="px-3 py-2 font-medium">{t.agent_name.replace(/_/g, " ")}</td>
                      <td className="px-3 py-2 text-muted-foreground">{t.instruction}</td>
                      <td className="px-3 py-2"><Badge variant={STATUS_VARIANT[t.status] ?? "glass"}>{t.status}</Badge></td>
                      <td className="px-3 py-2 text-right font-mono text-muted-foreground">{durationMs(t.started_at, t.completed_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <ShieldCheck className="h-4 w-4 text-primary" /> Evidence ({run?.evidence.length ?? 0})
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 p-3 md:grid-cols-2 xl:grid-cols-3">
          {(run?.evidence ?? []).map((e, i) => (
            <div key={i} className="rounded-xl border bg-background/80 p-3 text-[12px]">
              <div className="flex items-center justify-between">
                <span className="font-bold">{e.source}</span>
                {e.score != null && <Badge variant="glass">{e.score.toFixed(2)}</Badge>}
              </div>
              <div className="mt-1 font-medium">{e.title}</div>
              <p className="mt-1 line-clamp-4 text-muted-foreground">{e.content}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      {run && (
        <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Evidence · </span>
          Live orchestration run <span className="font-mono">{run.run_id}</span> at {run.created_at} — real
          supervisor-routed multi-agent execution via /agentic-ai/run.
        </div>
      )}
    </div>
  );
}
