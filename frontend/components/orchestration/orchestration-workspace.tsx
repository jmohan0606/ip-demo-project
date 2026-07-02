"use client";

import { useEffect, useState } from "react";
import { Bot, BrainCircuit, Network, PlayCircle, Workflow } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { runOrchestration } from "@/lib/api/orchestration";
import { AgentTraceStrip } from "@/components/integrated/common/agent-trace-strip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const workflows = [
  { id: "dashboard", label: "Dashboard Intelligence", icon: BrainCircuit },
  { id: "advisor_360", label: "Advisor 360", icon: Bot },
  { id: "recommendations", label: "Recommendations", icon: Workflow },
  { id: "what_if", label: "What-If Scenario", icon: PlayCircle },
  { id: "graph", label: "Graph Explorer", icon: Network },
  { id: "features_embeddings", label: "Features / Embeddings", icon: BrainCircuit },
  { id: "knowledge", label: "Knowledge Search", icon: Bot },
  { id: "memory_explainability", label: "Memory / Explainability", icon: Workflow }
];

export function OrchestrationWorkspace() {
  const context = useApiContextPayload();
  const [workflow, setWorkflow] = useState("dashboard");
  const [result, setResult] = useState<any | null>(null);

  async function run(selected = workflow) {
    setResult(null);
    setResult(await runOrchestration(selected, context, {
      query: "managed account growth playbook",
      meeting_increase_pct: 12,
      prospect_conversion_increase_pct: 8,
      managed_revenue_shift_pct: 6,
      nnm_increase_pct: 5,
      aum_increase_pct: 3
    }));
  }

  useEffect(() => { run(workflow); }, [workflow, context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <Badge variant="glass">Full End-to-End Backend Orchestration</Badge>
          <h2 className="mt-2 text-[22px] font-black">LangGraph-style Agent Workflow Runtime</h2>
          <p className="text-[12px] text-muted-foreground">Runs API → supervisor → specialist agents → tools → response with evidence and trace.</p>
        </div>
        <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={() => run()}>
          <PlayCircle className="h-4 w-4" />
          Run Workflow
        </Button>
      </div>

      <div className="grid gap-2 md:grid-cols-4">
        {workflows.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => setWorkflow(item.id)}
              className={workflow === item.id ? "compact-card compact-card-pad bg-ai-soft text-left" : "compact-card compact-card-pad text-left hover:bg-muted/60"}
            >
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-indigo-600" />
                <strong className="text-[12px]">{item.label}</strong>
              </div>
            </button>
          );
        })}
      </div>

      {!result ? <div className="h-[520px] animate-pulse rounded-xl bg-muted" /> : (
        <div className="grid gap-3 xl:grid-cols-[1fr_.95fr]">
          <Card>
            <CardHeader className="p-3"><CardTitle className="text-[13px]">Agent Execution Trace</CardTitle></CardHeader>
            <CardContent className="space-y-2 p-3">
              <AgentTraceStrip trace={result.orchestration_trace} />
              {result.orchestration_trace?.agents?.map((agent: any) => (
                <div key={agent.agent_name} className="compact-card compact-card-pad">
                  <div className="flex items-center justify-between">
                    <strong>{agent.agent_name}</strong>
                    <Badge variant="success">{agent.duration_ms} ms</Badge>
                  </div>
                  <div className="mt-1 text-[12px] text-muted-foreground">{agent.output}</div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {agent.tool_calls?.map((tool: any) => <Badge key={tool.tool_name} variant="glass">{tool.tool_name}</Badge>)}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="p-3"><CardTitle className="text-[13px]">Result / Evidence</CardTitle></CardHeader>
            <CardContent className="space-y-3 p-3">
              <div className="rounded-xl border bg-good-soft p-3 text-[12px]">
                <strong>Status:</strong> {result.orchestration_trace?.status}
              </div>
              <div className="rounded-xl border bg-ai-soft p-3">
                <div className="mb-2 text-[12px] font-black">Evidence</div>
                <div className="space-y-2">
                  {(result.evidence ?? []).map((e: any, index: number) => (
                    <div key={index} className="rounded-lg bg-background/80 p-2 text-[12px]">
                      <strong>{e.source ?? "Evidence"}:</strong> {e.summary ?? e.item ?? JSON.stringify(e)}
                    </div>
                  ))}
                </div>
              </div>
              <pre className="max-h-[420px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(result, null, 2)}</pre>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
