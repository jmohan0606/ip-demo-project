import type { AgentTraceStep } from "@/lib/types/memory_explainability";
import { Badge } from "@/components/ui/badge";

export function AgentTracePanel({ steps }: { steps: AgentTraceStep[] }) {
  return (
    <div className="space-y-3">
      {steps.map((step) => (
        <details key={step.agentName} className="rounded-2xl border border-border/70 bg-background/70 p-4">
          <summary className="cursor-pointer list-none">
            <div className="flex items-center justify-between gap-3">
              <div className="font-black">{step.agentName}</div>
              <div className="flex items-center gap-2">
                <Badge variant={step.status === "Completed" ? "success" : step.status === "Failed" ? "destructive" : "warning"}>{step.status}</Badge>
                <Badge variant="glass">{step.durationMs} ms</Badge>
              </div>
            </div>
          </summary>
          <div className="mt-4 grid gap-3 text-sm text-muted-foreground">
            <div><strong className="text-foreground">Input:</strong> {step.input}</div>
            <div><strong className="text-foreground">Output:</strong> {step.output}</div>
            <div className="flex flex-wrap gap-2">
              {step.toolCalls.map((tool) => <Badge key={tool} variant="secondary">{tool}</Badge>)}
            </div>
          </div>
        </details>
      ))}
    </div>
  );
}
