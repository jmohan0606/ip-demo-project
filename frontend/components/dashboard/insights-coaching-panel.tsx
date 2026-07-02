import { BrainCircuit, ChevronDown, ShieldCheck } from "lucide-react";
import type { CoachingInsight } from "@/lib/types/dashboard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function InsightsCoachingPanel({ insights }: { insights: CoachingInsight[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BrainCircuit className="h-5 w-5 text-primary" />
          Insights & Coaching Cards
        </CardTitle>
        <CardDescription>Evidence-backed AI reasoning with recommended actions.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {insights.map((insight) => (
          <details key={insight.id} className="group rounded-2xl border border-border/70 bg-background/70 p-4">
            <summary className="flex cursor-pointer list-none items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold">{insight.title}</h3>
                  <Badge variant={insight.severity === "High" ? "destructive" : insight.severity === "Medium" ? "warning" : "success"}>
                    {insight.severity}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{insight.summary}</p>
              </div>
              <ChevronDown className="h-4 w-4 shrink-0 transition group-open:rotate-180" />
            </summary>
            <div className="mt-4 grid gap-3 rounded-xl bg-muted/40 p-3 text-sm">
              <div>
                <div className="mb-1 font-bold">Evidence</div>
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {insight.evidence.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
              <div>
                <div className="mb-1 font-bold">Reasoning</div>
                <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
                  {insight.reasoningSteps.map((item) => <li key={item}>{item}</li>)}
                </ol>
              </div>
              <div>
                <div className="mb-1 flex items-center gap-1 font-bold">
                  <ShieldCheck className="h-4 w-4 text-success" />
                  Recommended Actions
                </div>
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {insight.recommendedActions.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            </div>
          </details>
        ))}
      </CardContent>
    </Card>
  );
}
