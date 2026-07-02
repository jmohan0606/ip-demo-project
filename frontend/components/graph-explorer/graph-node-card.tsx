import type { GraphExplorerNode } from "@/lib/types/graph_explorer";
import { Badge } from "@/components/ui/badge";

export function GraphNodeCard({ node }: { node: GraphExplorerNode }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="font-bold">{node.label}</div>
          <div className="text-xs text-muted-foreground">{node.id}</div>
        </div>
        <Badge variant="glass">{node.type}</Badge>
      </div>
      {node.description && <p className="mt-3 text-sm text-muted-foreground">{node.description}</p>}
      {node.score !== undefined && <div className="mt-3 text-sm">Score: <strong>{Math.round(node.score * 100)}%</strong></div>}
    </div>
  );
}
