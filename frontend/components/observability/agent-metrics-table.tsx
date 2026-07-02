import type { AgentRunMetric } from "@/lib/types/observability";
import { Badge } from "@/components/ui/badge";

export function AgentMetricsTable({ rows }: { rows: AgentRunMetric[] }) {
  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div key={row.agentName} className="grid gap-3 rounded-2xl border border-border/70 bg-background/70 p-4 md:grid-cols-6 md:items-center">
          <div className="font-bold md:col-span-2">{row.agentName}</div>
          <div><span className="text-muted-foreground">Runs</span><div>{row.executions}</div></div>
          <div><span className="text-muted-foreground">Success</span><div>{row.successRate}%</div></div>
          <div><span className="text-muted-foreground">Latency</span><div>{row.avgLatencyMs} ms</div></div>
          <Badge variant={row.failures <= 3 ? "success" : "warning"}>{row.failures} failures</Badge>
        </div>
      ))}
    </div>
  );
}
