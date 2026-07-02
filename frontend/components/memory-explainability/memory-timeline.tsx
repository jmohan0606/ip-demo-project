import type { MemoryTimelineItem } from "@/lib/types/memory_explainability";
import { Badge } from "@/components/ui/badge";

export function MemoryTimeline({ items }: { items: MemoryTimelineItem[] }) {
  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.memoryId} className="relative pl-8">
          <div className="absolute left-0 top-1 h-4 w-4 rounded-full bg-primary shadow-glow-blue" />
          {index < items.length - 1 && <div className="absolute left-[7px] top-5 h-full w-px bg-border" />}
          <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="font-black">{item.title}</div>
                <div className="text-xs text-muted-foreground">{item.timestamp} · {item.memoryId} · {item.sourceAgent}</div>
              </div>
              <Badge variant="glass">{item.memoryType}</Badge>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{item.summary}</p>
            <div className="mt-3 text-sm">Importance: <strong>{Math.round(item.importanceScore * 100)}%</strong></div>
          </div>
        </div>
      ))}
    </div>
  );
}
