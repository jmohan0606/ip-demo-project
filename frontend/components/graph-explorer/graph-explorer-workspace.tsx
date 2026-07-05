"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, { Background, Controls, MiniMap, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { Network } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import { fetchNeighborhood, type GraphNeighborhood, type GraphVizNode } from "@/lib/api/graph-viz";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { colors } from "@/styles/tokens";

// group -> node fill, mapped to the design tokens (AI artifacts on the indigo-blue
// AI-accent so the pipeline output stands out on the canvas).
const GROUP_COLOR: Record<string, string> = {
  advisor: colors.primary,
  org: "#64748B",
  household: colors.positive,
  crm: "#0EA5E9",
  agp: colors.warning,
  ai: colors.aiAccent,
};

const GROUP_LABEL: Record<string, string> = {
  advisor: "Advisor",
  org: "Org / Market",
  household: "Household",
  crm: "CRM",
  agp: "AGP",
  ai: "AI Pipeline",
};

function nodeStyle(group: string, focal: boolean): React.CSSProperties {
  const color = GROUP_COLOR[group] ?? "#64748B";
  return {
    borderRadius: 12,
    padding: focal ? "12px 16px" : "8px 10px",
    border: `1.5px solid ${color}`,
    background: focal ? color : "#0f172a",
    color: "white",
    fontSize: focal ? 12 : 10,
    fontWeight: 700,
    maxWidth: 150,
  };
}

// deterministic layout: focal advisor centered, every other node placed on a ring
// grouped by its group so related nodes cluster (no random positions).
function layout(data: GraphNeighborhood): Node[] {
  const cx = 430;
  const cy = 300;
  const focal = data.focal_advisor.id;
  const others = data.nodes.filter((n) => n.id !== focal);
  const byGroup = new Map<string, GraphVizNode[]>();
  others.forEach((n) => byGroup.set(n.group, [...(byGroup.get(n.group) ?? []), n]));
  const groups = [...byGroup.keys()];

  return data.nodes.map((n) => {
    if (n.id === focal) {
      return { id: n.id, position: { x: cx, y: cy }, data: { label: n.label }, style: nodeStyle(n.group, true) };
    }
    const gIdx = groups.indexOf(n.group);
    const groupNodes = byGroup.get(n.group)!;
    const within = groupNodes.indexOf(n);
    const baseAngle = (gIdx / groups.length) * Math.PI * 2;
    const angle = baseAngle + (within - (groupNodes.length - 1) / 2) * 0.28;
    const radius = 190 + (within % 2) * 78;
    return {
      id: n.id,
      position: { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) },
      data: { label: n.label },
      style: nodeStyle(n.group, false),
    };
  });
}

export function GraphExplorerWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [data, setData] = useState<GraphNeighborhood | null>(null);
  const [selected, setSelected] = useState<GraphVizNode | null>(null);

  useEffect(() => {
    apiClient
      .get<{ advisors: Array<{ advisor_id: string; advisor_name: string | null }> }>("/advisor/list")
      .then((r) => setAdvisors(r.advisors))
      .catch(() => setAdvisors([]));
  }, []);

  useEffect(() => {
    if (shell.scopeType === "Advisor") setAdvisorId(shell.scopeId);
    else resolveScope(shell.scopeType, shell.scopeId).then((r) => setAdvisorId(r.advisor_ids[0] ?? "A001")).catch(() => undefined);
  }, [shell.scopeType, shell.scopeId]);

  const load = useCallback(async () => {
    setSelected(null);
    setData(await fetchNeighborhood(advisorId));
  }, [advisorId]);

  useEffect(() => {
    void load();
  }, [load]);

  const nodes = useMemo(() => (data ? layout(data) : []), [data]);
  const edges: Edge[] = useMemo(
    () =>
      (data?.edges ?? []).map((e, i) => ({
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: true,
        style: { stroke: colors.surface.border },
        labelStyle: { fontSize: 9, fill: colors.text.muted },
      })),
    [data],
  );

  const advisorName = advisors.find((a) => a.advisor_id === advisorId)?.advisor_name ?? advisorId;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Knowledge Graph Explorer</Badge>
          <h2 className="mt-2 text-[22px] font-black">Relationship Explorer · {advisorName}</h2>
          <p className="text-[12px] text-muted-foreground">
            Real one-hop subgraph from the foundation graph — households, CRM, AGP and the AI
            pipeline artifacts (prediction → opportunity → recommendation) around this advisor.
          </p>
        </div>
        <select
          className="h-8 rounded-lg border border-border bg-background px-2 text-[12px]"
          value={advisorId}
          onChange={(e) => setAdvisorId(e.target.value)}
        >
          {advisors.length === 0 && <option value={advisorId}>{advisorId}</option>}
          {advisors.map((a) => (
            <option key={a.advisor_id} value={a.advisor_id}>
              {a.advisor_name ?? a.advisor_id}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.3fr_.7fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Network className="h-4 w-4 text-primary" /> Graph Canvas
            </CardTitle>
            <span className="text-[10px] text-muted-foreground">
              {data ? `${data.counts.nodes} nodes · ${data.counts.edges} edges` : "…"}
            </span>
          </CardHeader>
          <CardContent className="p-3">
            <div className="h-[560px] overflow-hidden rounded-xl border bg-slate-950">
              {data && (
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  fitView
                  onNodeClick={(_, node) => setSelected(data.nodes.find((n) => n.id === node.id) ?? null)}
                >
                  <Background color="#1e293b" />
                  <MiniMap pannable style={{ background: "#0f172a" }} />
                  <Controls />
                </ReactFlow>
              )}
            </div>
            <div className="mt-2 flex flex-wrap gap-3">
              {Object.entries(GROUP_LABEL).map(([g, label]) => (
                <span key={g} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: GROUP_COLOR[g] }} />
                  {label}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3">
            <CardTitle className="text-[13px]">Node Detail</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 p-3 text-[12px]">
            {!selected ? (
              <div className="rounded-xl border border-dashed p-6 text-center text-muted-foreground">
                Click any node to inspect its real attributes.
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: GROUP_COLOR[selected.group] }} />
                  <span className="font-bold">{selected.label}</span>
                  <Badge variant="glass" className="text-[10px]">{selected.type}</Badge>
                </div>
                <dl className="divide-y rounded-xl border">
                  {Object.entries(selected.attributes).slice(0, 14).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-3 px-3 py-1.5">
                      <dt className="text-muted-foreground">{k}</dt>
                      <dd className="truncate text-right font-mono">{String(v)}</dd>
                    </div>
                  ))}
                </dl>
              </>
            )}
            {data && (
              <div className="rounded-xl border bg-good-soft p-2 text-[10px] text-muted-foreground">
                <span className="font-semibold text-foreground">Evidence · </span>
                {data.evidence.source}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
