import type { PredictionDriver } from "@/lib/types/predictions_workspace";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function PredictionDriversPanel({ drivers }: { drivers: PredictionDriver[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Prediction Drivers</CardTitle>
        <CardDescription>Explainability for forecast movement and model output.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {drivers.map((driver) => (
          <div key={driver.driver} className="flex items-center justify-between rounded-2xl border border-border/70 bg-background/70 p-3">
            <div>
              <div className="font-bold">{driver.driver}</div>
              <div className="text-sm text-muted-foreground">Contribution: {driver.contribution > 0 ? "+" : ""}{driver.contribution}%</div>
            </div>
            <Badge variant={driver.direction === "Positive" ? "success" : driver.direction === "Negative" ? "destructive" : "glass"}>{driver.direction}</Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
