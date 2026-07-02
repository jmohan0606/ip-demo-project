import type { ToolCallAudit } from "@/lib/types/memory_explainability";
import { Badge } from "@/components/ui/badge";

export function ToolCallAuditPanel({ calls }: { calls: ToolCallAudit[] }) {
  return (
    <div className="space-y-3">
      {calls.map((call) => (
        <div key={`${call.system}-${call.toolName}`} className="grid gap-3 rounded-2xl border border-border/70 bg-background/70 p-4 md:grid-cols-5 md:items-center">
          <div className="font-bold">{call.toolName}</div>
          <Badge variant="glass">{call.system}</Badge>
          <Badge variant={call.status === "Success" ? "success" : call.status === "Fallback" ? "warning" : "destructive"}>{call.status}</Badge>
          <div className="text-sm text-muted-foreground">{call.durationMs} ms</div>
          <div className="text-sm text-muted-foreground">{call.resultSize}</div>
        </div>
      ))}
    </div>
  );
}
