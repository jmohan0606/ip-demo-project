import type { LearningLoopItem } from "@/lib/types/memory_explainability";
import { Badge } from "@/components/ui/badge";

export function LearningLoopPanel({ items }: { items: LearningLoopItem[] }) {
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.recommendationId} className="rounded-2xl border border-border/70 bg-background/70 p-4">
          <div className="flex items-center justify-between">
            <div className="font-black">{item.recommendationId}</div>
            <Badge variant={item.action === "Accepted" || item.action === "Completed" ? "success" : "warning"}>{item.action}</Badge>
          </div>
          <div className="mt-3 grid gap-2 text-sm text-muted-foreground">
            <div><strong className="text-foreground">Outcome:</strong> {item.outcome}</div>
            <div><strong className="text-foreground">Learning Signal:</strong> {item.learningSignal}</div>
            <div><strong className="text-foreground">Memory Update:</strong> {item.memoryUpdate}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
