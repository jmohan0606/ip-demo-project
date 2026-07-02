import type { WorkflowTrace } from "@/lib/types/observability";
import { Badge } from "@/components/ui/badge";

export function WorkflowTraceList({ traces }: { traces: WorkflowTrace[] }) {
  return (
    <div className="space-y-3">
      {traces.map((trace) => (
        <details key={trace.traceId} className="rounded-2xl border border-border/70 bg-background/70 p-4">
          <summary className="cursor-pointer list-none">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-black">{trace.workflowName}</div>
                <div className="text-xs text-muted-foreground">{trace.traceId} · {trace.startedAt}</div>
              </div>
              <div className="flex gap-2">
                <Badge variant={trace.status === "Healthy" ? "success" : "warning"}>{trace.status}</Badge>
                <Badge variant="glass">{trace.durationMs} ms</Badge>
                <Badge variant="secondary">{trace.activeMode}</Badge>
              </div>
            </div>
          </summary>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {trace.steps.map((step, index) => (
              <span key={`${trace.traceId}-${step}`} className="flex items-center gap-2">
                <Badge variant="glass">{step}</Badge>
                {index < trace.steps.length - 1 && <span className="text-muted-foreground">→</span>}
              </span>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
