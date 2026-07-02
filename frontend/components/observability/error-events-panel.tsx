import type { ErrorEvent } from "@/lib/types/observability";
import { Badge } from "@/components/ui/badge";

export function ErrorEventsPanel({ events }: { events: ErrorEvent[] }) {
  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div key={event.eventId} className="rounded-2xl border border-border/70 bg-background/70 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-black">{event.source}</div>
              <div className="text-xs text-muted-foreground">{event.eventId} · {event.timestamp}</div>
            </div>
            <Badge variant={event.severity === "Critical" || event.severity === "High" ? "destructive" : event.severity === "Medium" ? "warning" : "glass"}>{event.severity}</Badge>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">{event.message}</p>
          <div className="mt-3 rounded-xl bg-muted/50 p-3 text-sm"><strong>Resolution:</strong> {event.resolution}</div>
        </div>
      ))}
    </div>
  );
}
