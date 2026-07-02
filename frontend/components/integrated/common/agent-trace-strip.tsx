import { CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function AgentTraceStrip({ trace }: { trace?: any }) {
  if (!trace?.agents) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {trace.agents.map((agent: any) => (
        <Badge key={agent.agent_name} variant="success" className="gap-1 text-[10px]">
          <CheckCircle2 className="h-3 w-3" />
          {agent.agent_name}
        </Badge>
      ))}
    </div>
  );
}
