import type { PerformerRow } from "@/lib/types/dashboard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";

export function PerformerTable({ title, rows, tone = "default" }: { title: string; rows: PerformerRow[]; tone?: "default" | "risk" }) {
  return (
    <Card className={tone === "risk" ? "risk-gradient" : undefined}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>Revenue, growth and AGP status.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map((row) => (
          <div key={row.advisorId} className="rounded-2xl border border-border/70 bg-background/70 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="font-bold">#{row.rank} {row.advisorName}</div>
                <div className="text-xs text-muted-foreground">{row.market} · {row.advisorId}</div>
              </div>
              <Badge variant={row.agpStatus === "On Track" ? "success" : row.agpStatus === "Off Track" ? "destructive" : row.agpStatus === "At Risk" ? "warning" : "glass"}>
                {row.agpStatus}
              </Badge>
            </div>
            <div className="mt-3 flex items-center justify-between text-sm">
              <span className="font-semibold">{formatCurrency(row.revenue)}</span>
              <span className={row.growth >= 0 ? "text-success" : "text-destructive"}>{row.growth >= 0 ? "+" : ""}{row.growth}%</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
