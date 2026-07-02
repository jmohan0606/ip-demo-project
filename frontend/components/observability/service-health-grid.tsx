import type { ServiceHealth } from "@/lib/types/observability";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function ServiceHealthGrid({ services }: { services: ServiceHealth[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {services.map((service) => (
        <Card key={service.serviceName}>
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-black">{service.serviceName}</div>
                <div className="text-xs text-muted-foreground">{service.category} · {service.mode}</div>
              </div>
              <Badge variant={service.status === "Healthy" ? "success" : service.status === "Warning" ? "warning" : "destructive"}>{service.status}</Badge>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-muted-foreground">Latency</span><div className="font-bold">{service.latencyMs} ms</div></div>
              <div><span className="text-muted-foreground">Success</span><div className="font-bold">{service.successRate}%</div></div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">Last checked: {service.lastChecked}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
