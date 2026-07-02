import { BarChart3, Database, DollarSign, PieChart, Users, UsersRound } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
const icons = { DollarSign, Users, PieChart, UsersRound, BarChart3, Database };
export function CompactKpiCard({ item }: { item: any }) {
  const Icon = icons[item.icon as keyof typeof icons] ?? DollarSign;
  const color = item.status === "bad" ? "bg-bad-soft status-bad" : item.status === "warn" ? "bg-warn-soft status-warn" : "bg-good-soft status-good";
  return (
    <div className="compact-card compact-kpi">
      <div className="flex items-start justify-between">
        <div><div className="compact-label">{item.label}</div><div className="compact-kpi-value">{item.display}</div><div className="text-[11px] text-muted-foreground">vs PY</div></div>
        <div className={cn("rounded-lg p-2", color)}><Icon className="h-4 w-4" /></div>
      </div>
      <Badge variant={item.status === "bad" ? "destructive" : item.status === "warn" ? "warning" : "success"} className="mt-2 text-[10px]">{item.change > 0 ? "+" : ""}{item.change}%</Badge>
    </div>
  );
}
