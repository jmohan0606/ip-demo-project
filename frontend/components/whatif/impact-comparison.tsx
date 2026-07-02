"use client";

import type { ScenarioImpact } from "@/lib/types/whatif";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";

function Row({ label, baseline, projected, currency = true }: { label: string; baseline: number; projected: number; currency?: boolean }) {
  const delta = projected - baseline;
  const pct = baseline ? (delta / baseline) * 100 : 0;
  return (
    <div className="grid grid-cols-4 items-center gap-3 rounded-2xl border border-border/70 bg-background/70 p-3 text-sm">
      <div className="font-bold">{label}</div>
      <div>{currency ? formatCurrency(baseline) : `${baseline.toFixed(1)}%`}</div>
      <div>{currency ? formatCurrency(projected) : `${projected.toFixed(1)}%`}</div>
      <Badge variant={delta >= 0 ? "success" : "destructive"}>{pct >= 0 ? "+" : ""}{pct.toFixed(1)}%</Badge>
    </div>
  );
}

export function ImpactComparison({ impact }: { impact: ScenarioImpact }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Baseline vs Scenario Impact</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-4 gap-3 px-3 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">
          <div>Metric</div><div>Baseline</div><div>Scenario</div><div>Change</div>
        </div>
        <Row label="Revenue" baseline={impact.baselineRevenue} projected={impact.projectedRevenue} />
        <Row label="NNM" baseline={impact.baselineNnm} projected={impact.projectedNnm} />
        <Row label="AUM" baseline={impact.baselineAum} projected={impact.projectedAum} />
        <Row label="Goal Attainment" baseline={impact.baselineGoalAttainment} projected={impact.projectedGoalAttainment} currency={false} />
        <div className="rounded-2xl border border-border/70 bg-muted/40 p-4">
          <div className="text-sm text-muted-foreground">AGP Status Movement</div>
          <div className="mt-2 flex items-center gap-3">
            <Badge variant="warning">{impact.agpStatusBefore}</Badge>
            <span>→</span>
            <Badge variant={impact.agpStatusAfter === "On Track" ? "success" : "warning"}>{impact.agpStatusAfter}</Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
