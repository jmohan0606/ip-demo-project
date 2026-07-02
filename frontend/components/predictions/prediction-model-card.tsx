import type { PredictionModelCard as PredictionModelCardType } from "@/lib/types/predictions_workspace";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function PredictionModelCard({ model }: { model: PredictionModelCardType }) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="font-black">{model.name}</div>
            <div className="text-sm text-muted-foreground">{model.modelId} · {model.modelType}</div>
          </div>
          <Badge variant={model.status === "Active" ? "success" : model.status === "Fallback" ? "warning" : "destructive"}>{model.status}</Badge>
        </div>
        <div className="mt-4 text-sm">
          Confidence: <strong>{Math.round(model.confidence * 100)}%</strong>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">{model.explanation}</p>
      </CardContent>
    </Card>
  );
}
