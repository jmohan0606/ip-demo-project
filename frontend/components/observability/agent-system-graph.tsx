"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, { Background, Controls, Position, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { Network } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import type { AgenticRun } from "@/lib/api/agentic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { colors } from "@/styles/tokens";

interface TopologyNode {
  id: string;
  kind: "supervisor" | "agent" | "tool" | "datasource";
  label: string;
  description: string;
  class_name?: string;
  invoked_when: string;
  order: number;
}
interface TopologyEdge { source: string; target: string; kind: string; label: string }
interface Topology {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  execution_order: string[];
  always_on: string[];
}

const KIND_COLOR: Record<string, string> = {
  supervisor: colors.primary,
  agent: colors.aiAccent,
  tool: "#0EA5E9",
  datasource: "#64748B",
};
const KIND_LABEL: Record<string, string> = {
  supervisor: "Supervisor",
  agent: "Agent",
  tool: "Tool / Service",
  datasource: "Data Source",
};

// Layered left-to-right layout: supervisor → agents (in real execution order) →
// tools → data sources. Deterministic, no random positions.
const COL_X: Record<string, number> = { supervisor: 0, agent: 300, tool: 680, datasource: 1010 };
const ROW_H: Record<string, number> = { supervisor: 0, agent: 64, tool: 76, datasource: 130 };

function layout(topo: Topology): Map<string, { x: number; y: number }> {
  const pos = new Map<string, { x: number; y: number }>();
  const agents = topo.nodes
    .filter((n) => n.kind === "agent")
    .sort((a, b) => a.order - b.order);
  const tools = topo.nodes.filter((n) => n.kind === "tool");
  const sources = topo.nodes.filter((n) => n.kind === "datasource");
  const agentH = (agents.length - 1) * ROW_H.agent;
  pos.set("supervisor", { x: COL_X.supervisor, y: agentH / 2 });
  agents.forEach((n, i) => pos.set(n.id, { x: COL_X.agent, y: i * ROW_H.agent }));
  tools.forEach((n, i) => pos.set(n.id, { x: COL_X.tool, y: i * ROW_H.tool + (agentH - (tools.length - 1) * ROW_H.tool) / 2 }));
  sources.forEach((n, i) => pos.set(n.id, { x: COL_X.datasource, y: i * ROW_H.datasource + (agentH - (sources.length - 1) * ROW_H.datasource) / 2 }));
  return pos;
}

function taskDurationMs(run: AgenticRun, agent: string): number | null {
  const t = run.tasks.find((x) => x.agent_name === agent);
  if (!t?.started_at || !t.completed_at) return null;
  const ms = new Date(t.completed_at).getTime() - new Date(t.started_at).getTime();
  return Number.isFinite(ms) && ms >= 0 ? ms : null;
}

export function AgentSystemGraph({ run }: { run: AgenticRun | null }) {
  const [topo, setTopo] = useState<Topology | null>(null);
  const [selected, setSelected] = useState<TopologyNode | null>(null);
  // Progressive replay of the REAL recorded route: revealedSteps counts how many
  // executed agents are currently highlighted (drives the animation).
  const [revealed, setRevealed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    apiClient.get<Topology>("/agentic-ai/topology").then(setTopo).catch(() => setTopo(null));
  }, []);

  // The executed path for THIS run, from the real recorded route plan. A run the
  // input guardrails blocked never reached the supervisor — highlight nothing.
  const executedPath = useMemo(
    () => (run && run.final_agent !== "guardrails" ? ["supervisor", ...run.route_plan] : []),
    [run],
  );

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    setRevealed(0);
    if (!run || executedPath.length === 0) return;
    let step = 0;
    timerRef.current = setInterval(() => {
      step += 1;
      setRevealed(step);
      if (step >= executedPath.length && timerRef.current) clearInterval(timerRef.current);
    }, 450);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [run, executedPath]);

  const activeSet = useMemo(() => new Set(executedPath.slice(0, revealed)), [executedPath, revealed]);
  // Tools/data sources touched by executed agents light up once their agent is revealed.
  const activeAux = useMemo(() => {
    if (!topo) return new Set<string>();
    const aux = new Set<string>();
    topo.edges.forEach((e) => {
      if (e.kind === "uses" && activeSet.has(e.source)) aux.add(e.target);
    });
    topo.edges.forEach((e) => {
      if (e.kind === "reads" && aux.has(e.source)) aux.add(e.target);
    });
    return aux;
  }, [topo, activeSet]);

  const nodes: Node[] = useMemo(() => {
    if (!topo) return [];
    const pos = layout(topo);
    return topo.nodes.map((n) => {
      const executedIdx = executedPath.indexOf(n.id);
      const isActive = activeSet.has(n.id) || activeAux.has(n.id);
      const dimmed = run != null && !isActive;
      const failed = run?.tasks.some((t) => t.agent_name === n.id && t.status === "failed");
      const border = failed ? colors.negative : KIND_COLOR[n.kind];
      const dur = run && executedIdx > 0 ? taskDurationMs(run, n.id) : null;
      const seq = executedIdx >= 0 && activeSet.has(n.id) ? `${executedIdx + 1}. ` : "";
      return {
        id: n.id,
        position: pos.get(n.id) ?? { x: 0, y: 0 },
        data: { label: `${seq}${n.label}${dur != null ? ` · ${dur} ms` : ""}` },
        style: {
          borderRadius: 10,
          padding: n.kind === "supervisor" ? "12px 14px" : "7px 10px",
          border: `1.5px solid ${border}`,
          background: isActive ? border : "#0f172a",
          color: "white",
          fontSize: n.kind === "agent" || n.kind === "supervisor" ? 11 : 10,
          fontWeight: 700,
          opacity: dimmed ? 0.35 : 1,
          maxWidth: 210,
          transition: "background .3s, opacity .3s",
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };
    });
  }, [topo, run, executedPath, activeSet, activeAux]);

  const edges: Edge[] = useMemo(() => {
    if (!topo) return [];
    const out: Edge[] = topo.edges.map((e, i) => {
      const active =
        (e.kind === "routes" && activeSet.has(e.target)) ||
        (e.kind === "uses" && activeSet.has(e.source)) ||
        (e.kind === "reads" && activeAux.has(e.source) && activeAux.has(e.target));
      return {
        id: `t-${i}`,
        source: e.source,
        target: e.target,
        label: e.kind === "routes" ? e.label : undefined,
        animated: active,
        style: {
          stroke: active ? KIND_COLOR.agent : colors.surface.border,
          strokeWidth: active ? 2 : 1,
          opacity: run != null && !active ? 0.25 : 1,
        },
        labelStyle: { fontSize: 8, fill: colors.text.muted },
      };
    });
    // Overlay the REAL executed sequence (the linear LangGraph route) as ordered edges.
    executedPath.slice(0, Math.max(revealed, 0)).forEach((id, i) => {
      const next = executedPath[i + 1];
      if (!next || !activeSet.has(next)) return;
      out.push({
        id: `run-${i}`,
        source: id,
        target: next,
        animated: true,
        label: `step ${i + 1}`,
        style: { stroke: colors.positive, strokeWidth: 2.5 },
        labelStyle: { fontSize: 9, fill: colors.positive, fontWeight: 700 },
      });
    });
    return out;
  }, [topo, run, executedPath, revealed, activeSet, activeAux]);

  const connections = useMemo(() => {
    if (!topo || !selected) return [];
    return topo.edges
      .filter((e) => e.source === selected.id || e.target === selected.id)
      .map((e) => {
        const otherId = e.source === selected.id ? e.target : e.source;
        const other = topo.nodes.find((n) => n.id === otherId);
        const dir = e.source === selected.id ? "→" : "←";
        return `${dir} ${other?.label ?? otherId} (${e.kind})`;
      });
  }, [topo, selected]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between p-3">
        <CardTitle className="flex items-center gap-2 text-[13px]">
          <Network className="h-4 w-4 text-primary" /> Live Agent System Graph
        </CardTitle>
        <span className="text-[10px] text-muted-foreground">
          {topo ? `${topo.nodes.length} nodes · ${topo.edges.length} edges — enumerated from the agent registry & supervisor routing rules` : "…"}
          {run ? ` · replaying route of ${run.run_id}` : ""}
        </span>
      </CardHeader>
      <CardContent className="p-3">
        <div className="grid gap-3 xl:grid-cols-[1.45fr_.55fr]">
          <div className="h-[460px] overflow-hidden rounded-xl border bg-slate-950">
            {topo && (
              <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                onNodeClick={(_, node) => setSelected(topo.nodes.find((n) => n.id === node.id) ?? null)}
              >
                <Background color="#1e293b" />
                <Controls />
              </ReactFlow>
            )}
          </div>
          <div className="space-y-2 text-[12px]">
            {!selected ? (
              <div className="rounded-xl border border-dashed p-5 text-center text-muted-foreground">
                Click any node for its purpose, when it&apos;s invoked, and its connections.
                After a run, the green &quot;step n&quot; edges replay the actual recorded route.
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: KIND_COLOR[selected.kind] }} />
                  <span className="font-bold">{selected.label}</span>
                  <Badge variant="glass" className="text-[10px]">{KIND_LABEL[selected.kind]}</Badge>
                </div>
                <p className="text-muted-foreground">{selected.description}</p>
                {selected.invoked_when && (
                  <p className="rounded-lg border bg-background/60 p-2 text-[11px]">
                    <span className="font-semibold">Invoked: </span>{selected.invoked_when}
                  </p>
                )}
                {run && executedPath.includes(selected.id) && (
                  <p className="rounded-lg border bg-good-soft p-2 text-[11px]">
                    <span className="font-semibold">This run: </span>
                    step {executedPath.indexOf(selected.id) + 1} of {executedPath.length}
                    {taskDurationMs(run, selected.id) != null ? ` · ${taskDurationMs(run, selected.id)} ms` : ""}
                  </p>
                )}
                <div className="rounded-lg border p-2">
                  <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Connections</div>
                  <ul className="space-y-0.5 text-[11px] text-muted-foreground">
                    {connections.map((c, i) => (<li key={i}>{c}</li>))}
                  </ul>
                </div>
              </div>
            )}
            <div className="flex flex-wrap gap-3 pt-1">
              {Object.entries(KIND_LABEL).map(([k, label]) => (
                <span key={k} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: KIND_COLOR[k] }} />
                  {label}
                </span>
              ))}
              <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <span className="h-0.5 w-4" style={{ backgroundColor: colors.positive }} />
                Executed path (this run)
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
