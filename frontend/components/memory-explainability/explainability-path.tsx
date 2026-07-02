import type { ExplainabilityPathStep } from "@/lib/types/memory_explainability";
import { Badge } from "@/components/ui/badge";

export function ExplainabilityPath({ steps }: { steps: ExplainabilityPathStep[] }) {
  return (
    <div className="space-y-3">
      {steps.map((step, index) => (
        <div key={step.stepId} className="rounded-2xl border border-border/70 bg-background/70 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-black">{index + 1}. {step.label}</div>
              <p className="mt-1 text-sm text-muted-foreground">{step.description}</p>
            </div>
            <Badge variant={step.nodeType === "Recommendation" ? "success" : "glass"}>{step.nodeType}</Badge>
          </div>
          <div className="mt-3 text-sm">Confidence: <strong>{Math.round(step.confidence * 100)}%</strong></div>
        </div>
      ))}
    </div>
  );
}
