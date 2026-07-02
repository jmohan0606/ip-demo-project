"use client";

import { BarChart3, CheckCircle2, DollarSign, TrendingUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/cards/kpi-card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";

const rows = [
  { id: "REC-001", title: "Managed Account Review", expected: 145000, actual: 121000, status: "Completed", signal: "+0.08" },
  { id: "REC-002", title: "NNM Recovery Sequence", expected: 64000, actual: 38000, status: "Accepted", signal: "+0.04" },
  { id: "REC-003", title: "AGP Meeting Plan", expected: 42000, actual: 0, status: "In Progress", signal: "Pending" }
];

export function RecommendationROIWorkspace() {
  return (
    <div className="animate-slide-up space-y-6">
      <div>
        <Badge variant="glass">Recommendation Impact / ROI</Badge>
        <h2 className="mt-3 text-3xl font-black tracking-tight">Recommendation Outcome Intelligence</h2>
        <p className="mt-2 text-muted-foreground">Track expected vs actual impact, adoption, outcomes, and learning signals.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Accepted Recommendations" value="74%" change="+9.1%" icon={CheckCircle2} variant="insight" />
        <KpiCard label="Revenue Impact" value="$1.2M" change="+12.4%" icon={DollarSign} />
        <KpiCard label="NNM Impact" value="$8.7M" change="+5.9%" icon={TrendingUp} variant="insight" />
        <KpiCard label="Learning Signals" value="128" change="+21" icon={BarChart3} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Expected vs Actual Impact</CardTitle>
          <CardDescription>Recommendation-level attribution and feedback learning visibility.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {rows.map((row) => (
            <div key={row.id} className="grid gap-3 rounded-2xl border border-border/70 bg-background/70 p-4 md:grid-cols-5 md:items-center">
              <div className="font-bold">{row.title}</div>
              <div><span className="text-muted-foreground">Expected</span><div>{formatCurrency(row.expected)}</div></div>
              <div><span className="text-muted-foreground">Actual</span><div>{formatCurrency(row.actual)}</div></div>
              <Badge variant={row.status === "Completed" ? "success" : "warning"}>{row.status}</Badge>
              <div><span className="text-muted-foreground">Learning</span><div className="font-bold">{row.signal}</div></div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
