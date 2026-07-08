"use client";
import { type } from "@/styles/tokens";
import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, PlayCircle, Workflow, ShieldCheck, Network, Brain, Sparkles } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import { runAgenticWorkflow, type AgenticRun } from "@/lib/api/agentic";
import { fetchAdapterStatus, type AdapterStatus } from "@/lib/api/admin";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { LoadingState, ErrorState } from "@/components/patterns/async-state";
import { AgentSystemGraph } from "@/components/observability/agent-system-graph";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "glass"> = {
  completed: "success", running: "warning", pending: "glass", failed: "destructive",
};

const DEFAULT_QUESTION = "How can this advisor grow revenue?";

function durationMs(a: string | null, b: string | null): string {
  if (!a || !b) return "—";
  const ms = new Date(b).getTime() - new Date(a).getTime();
  return Number.isFinite(ms) && ms >= 0 ? `${ms} ms` : "—";
}

// Compact one-line rendering of an agent task's REAL result payload (what the
// agent actually decided/produced this run) — scalars only, nested blobs skipped.
function decisionSummary(result: Record<string, unknown> | undefined): string {
  if (!result) return "—";
  const parts: string[] = [];
  for (const [k, v] of Object.entries(result)) {
    if (v == null) continue;
    if (Array.isArray(v)) parts.push(`${k}: ${v.length <= 4 && v.every((x) => typeof x === "string") ? v.join(" → ") : `${v.length} items`}`);
    else if (typeof v === "object") continue;
    else parts.push(`${k}: ${typeof v === "number" ? Number(v.toFixed ? v.toFixed(2) : v) : String(v)}`);
  }
  return parts.slice(0, 5).join(" · ") || "—";
}

const GUARDRAIL_ACTION_VARIANT: Record<string, "success" | "warning" | "destructive" | "glass"> = {
  ALLOW: "success", FLAG: "warning", REDACT: "warning", BLOCK: "destructive",
};
const COMPLIANCE_VARIANT: Record<string, "success" | "warning" | "destructive" | "glass"> = {
  PASSED: "success", NEEDS_REVIEW: "warning", NEEDS_DISCLOSURE: "warning", BLOCKED: "destructive",
};

export function SystemObservabilityWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  // Starts empty so the guidance placeholder shows; runs fall back to the example
  // question until the user types their own.
  const [question, setQuestion] = useState("");
  const [run, setRun] = useState<AgenticRun | null>(null);
  const [adapters, setAdapters] = useState<AdapterStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  // Monotonic sequence so an older in-flight run can never overwrite a newer one
  // (advisor-change auto-runs and manual runs can overlap).
  const runSeq = useRef(0);
  const execute = useCallback(async () => {
    const seq = ++runSeq.current;
    setBusy(true);
    setError(null);
    try {
      const result = await runAgenticWorkflow(question.trim() || DEFAULT_QUESTION, advisorId);
      if (seq === runSeq.current) setRun(result);
    } catch (e) {
      if (seq === runSeq.current) setError(e instanceof Error ? e.message : "Workflow run failed");
    } finally {
      if (seq === runSeq.current) setBusy(false);
    }
  }, [question, advisorId]);

  useEffect(() => {
    void execute();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [advisorId]);

  // Show the tier that ACTUALLY serves graph requests, not just the configured mode —
  // configured `tiered:real` can still be served by the mock tier when no live engine
  // is reachable, and hiding that difference is exactly what a "real" label must not do.
  const graphActiveTier = adapters?.graph.active_tier_name;
  const graphServingLive = graphActiveTier != null && graphActiveTier !== "mock";
  const services = adapters
    ? [
        {
          icon: <Network className="h-4 w-4" />,
          name: "Graph Client",
          mode: graphActiveTier ? `serving: ${graphActiveTier}` : adapters.graph.mode,
          healthy: adapters.graph.healthy,
          warn: graphActiveTier != null && !graphServingLive && adapters.graph_client_mode !== "mock",
          detail: `${adapters.graph.graph} · configured ${adapters.graph_client_mode} (${adapters.graph.mode})${
            adapters.graph.active_tier != null ? ` · active tier ${adapters.graph.active_tier} of 4` : ""
          }`,
        },
        { icon: <Brain className="h-4 w-4" />, name: "LLM Client", mode: adapters.llm.mode, healthy: true, warn: false, detail: adapters.llm.model },
        { icon: <Sparkles className="h-4 w-4" />, name: "Embedding Client", mode: adapters.embedding.mode, healthy: true, warn: false, detail: `${adapters.embedding.model} · ${adapters.embedding.dimensions}d` },
      ]
    : [];

  return (
    <div className="space-y-3">
      <div>
        <Badge variant="glass">Agent Orchestration &amp; Observability</Badge>
        <h2 className={`mt-2 ${type.pageTitle}`}>Live Multi-Agent Workflow Trace</h2>
        <p className="text-[12px] text-muted-foreground">
          Runs the real supervisor→agents orchestration (`/agentic-ai/run`) and shows the actual
          route, per-agent tasks, evidence and confidence — plus live adapter modes. No simulated
          metrics.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-2 p-3">
          <p className="text-[12px] text-muted-foreground">
            Enter a question and run it through the live multi-agent system — the sections below
            show the real agents, evidence, and reasoning that produce the answer.
          </p>
          <div className="flex flex-wrap items-stretch gap-2">
            <textarea
              rows={3}
              className="min-h-[76px] flex-1 basis-[420px] resize-y rounded-lg border border-border bg-background px-3 py-2 text-[13px] leading-relaxed placeholder:text-muted-foreground/70 focus:outline-none focus:ring-2 focus:ring-primary/40"
              placeholder={"Ask a question about this advisor — e.g. 'How can this advisor grow revenue?' or 'What should I coach them on, and are the recommendations compliant?' — then press Run Workflow"}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <div className="flex w-56 flex-col justify-between gap-2">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Advisor</span>
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
              </div>
              <Button variant="premium" className="h-9 w-full gap-2 text-[12px]" onClick={execute} disabled={busy}>
                <PlayCircle className="h-4 w-4" /> {busy ? "Running…" : "Run Workflow"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {error && !run ? (
        <ErrorState message="The agent workflow couldn't complete. Check the backend is running, then retry." onRetry={() => void execute()} />
      ) : busy && !run ? (
        <LoadingState label="Running agent workflow — orchestrating agents, gathering evidence…" />
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Final Agent" value={run ? run.final_agent.replace(/_/g, " ") : "—"} />
        <KpiStatCard label="Confidence" value={run ? `${(run.confidence * 100).toFixed(0)}%` : "—"} />
        <KpiStatCard label="Agent Tasks" value={String(run?.tasks.length ?? "—")} />
        <KpiStatCard label="Evidence Items" value={String(run?.evidence.length ?? "—")} />
      </div>

      {run?.confidence_breakdown && (
        <div className="rounded-xl border bg-background/60 px-3 py-2 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">How Confidence Was Computed · </span>
          {run.confidence_breakdown.formula} ={" "}
          <span className="font-mono">
            task success {(run.confidence_breakdown.components.task_success_rate * 100).toFixed(0)}% ·
            evidence coverage {(run.confidence_breakdown.components.evidence_coverage * 100).toFixed(0)}% ·
            answer {run.confidence_breakdown.components.llm_authored ? "LLM-authored" : "deterministic fallback"} ·
            model confidence {(run.confidence_breakdown.components.model_confidence * 100).toFixed(0)}%
            ({run.confidence_breakdown.components.model_confidence_source})
          </span>
        </div>
      )}

      <div className="grid gap-3 xl:grid-cols-3">
        {services.map((s) => (
          <Card key={s.name}>
            <CardHeader className="flex flex-row items-center justify-between p-3">
              <CardTitle className="flex items-center gap-2 text-[13px]">{s.icon} {s.name}</CardTitle>
              <Badge variant={s.warn ? "warning" : s.healthy ? "success" : "destructive"}>{s.mode}</Badge>
            </CardHeader>
            <CardContent className="p-3 text-[12px] text-muted-foreground">{s.detail}</CardContent>
          </Card>
        ))}
      </div>

      <AgentSystemGraph run={run} />

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
                    <th className="px-3 py-2">Decision / Output</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2 text-right">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {(run?.tasks ?? []).map((t) => (
                    <tr key={t.task_id} className="border-b last:border-0">
                      <td className="px-3 py-2 font-medium">{t.agent_name.replace(/_/g, " ")}</td>
                      <td className="px-3 py-2 text-muted-foreground">{t.instruction}</td>
                      <td className="px-3 py-2 font-mono text-[10px] text-muted-foreground">{t.error ?? decisionSummary(t.result)}</td>
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

      {run?.guardrails && (
        <div className="grid gap-3 xl:grid-cols-2">
          {(["input", "output"] as const).map((stage) => {
            const g = run.guardrails?.[stage];
            if (!g) return null;
            return (
              <Card key={stage}>
                <CardHeader className="flex flex-row items-center justify-between p-3">
                  <CardTitle className="flex items-center gap-2 text-[13px]">
                    <ShieldCheck className="h-4 w-4 text-primary" />
                    {stage === "input" ? "Input Guardrails (Question)" : "Output Guardrails (Answer)"}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    {g.grounding_score != null && (
                      <Badge variant="glass">grounding {(g.grounding_score * 100).toFixed(0)}%</Badge>
                    )}
                    <Badge variant={GUARDRAIL_ACTION_VARIANT[g.action] ?? "glass"}>{g.action}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-3 text-[12px]">
                  {g.findings.length === 0 ? (
                    <p className="text-muted-foreground">
                      No findings — this run&apos;s {stage === "input" ? "question passed injection/jailbreak/PII screening" : "answer passed PII/grounding screening"}.
                    </p>
                  ) : (
                    <ul className="space-y-1.5">
                      {g.findings.map((f, i) => (
                        <li key={i} className="rounded-lg border bg-background/60 p-2">
                          <div className="flex items-center gap-2">
                            <Badge variant={GUARDRAIL_ACTION_VARIANT[f.action] ?? "glass"} className="text-[9px]">{f.action}</Badge>
                            <span className="font-semibold">{f.category}</span>
                            <span className="text-[10px] text-muted-foreground">{f.severity} · {f.matched_rule}</span>
                          </div>
                          <p className="mt-1 text-muted-foreground">{f.detail}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {run?.compliance_review && run.compliance_review.reviews.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <ShieldCheck className="h-4 w-4 text-primary" /> Compliance Review (This Run)
            </CardTitle>
            <div className="flex items-center gap-1.5">
              {Object.entries(run.compliance_review.status_counts).map(([s, n]) => (
                <Badge key={s} variant={COMPLIANCE_VARIANT[s] ?? "glass"}>{s.replace(/_/g, " ")} × {n}</Badge>
              ))}
            </div>
          </CardHeader>
          <CardContent className="p-3 text-[12px]">
            <p className="mb-2 text-[11px] text-muted-foreground">
              Rules evaluated on every generated recommendation: {run.compliance_review.rules_evaluated.join(", ")}.
            </p>
            <ul className="grid gap-2 md:grid-cols-2">
              {run.compliance_review.reviews.map((r, i) => (
                <li key={i} className="rounded-lg border bg-background/60 p-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-mono text-[10px]">{r.recommendation_id}</span>
                    <Badge variant={COMPLIANCE_VARIANT[r.status] ?? "glass"} className="text-[9px]">{r.status.replace(/_/g, " ")}</Badge>
                  </div>
                  {r.flags.map((f, j) => (
                    <p key={j} className="mt-1 text-muted-foreground">[{f.rule}] {f.detail}</p>
                  ))}
                  {r.flags.length === 0 && <p className="mt-1 text-muted-foreground">All rules passed.</p>}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

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
