"use client";

import { useEffect, useState } from "react";
import { BrainCircuit, Database, GitBranch, LineChart, Search } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { fetchFeatureRuntimeStatus, fetchFeatureVector, fetchSimilarity, runPrediction } from "@/lib/api/feature-runtime";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";

export function FeatureRuntimeWorkspace() {
  const context = useApiContextPayload();
  const [status, setStatus] = useState<any | null>(null);
  const [features, setFeatures] = useState<any | null>(null);
  const [similarity, setSimilarity] = useState<any | null>(null);
  const [prediction, setPrediction] = useState<any | null>(null);

  async function refresh() {
    setStatus(await fetchFeatureRuntimeStatus());
    setFeatures(await fetchFeatureVector(context));
    setSimilarity(await fetchSimilarity(context));
    setPrediction(await runPrediction(context, {
      meeting_increase_pct: 12,
      prospect_conversion_increase_pct: 8,
      managed_revenue_shift_pct: 6,
      nnm_increase_pct: 5
    }));
  }

  useEffect(() => { refresh(); }, [context.persona, context.scope_type, context.scope_id, context.period, context.compare_to]);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <Badge variant="glass">Feature Store & Prediction Platform</Badge>
          <h2 className="mt-2 text-[22px] font-black">Feature Vectors, Similarity & Forecasting</h2>
          <p className="text-[12px] text-muted-foreground">SQLite feature store with graph persistence, similarity search and transparent prediction runtime.</p>
        </div>
        <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={refresh}><Database className="h-4 w-4" />Refresh</Button>
      </div>

      <div className="grid gap-3 xl:grid-cols-4">
        <Card className="bg-ai-soft">
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Database className="h-4 w-4" />Store Status</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3 text-[12px]">
            <div>Backend: <strong>{status?.feature_store_backend}</strong></div>
            <div>Vectors: <strong>{status?.feature_vectors}</strong></div>
            <div>Predictions: <strong>{status?.prediction_results}</strong></div>
            <div>Graph embeddings: <strong>{status?.graph_embedding_backend}</strong></div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-3">
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><GitBranch className="h-4 w-4" />Selected Feature Vector</CardTitle></CardHeader>
          <CardContent className="grid gap-2 p-3 md:grid-cols-4">
            {features?.features && Object.entries(features.features).slice(0, 12).map(([key, value]: any) => (
              <div key={key} className="rounded-xl border bg-background p-2 text-[12px]">
                <div className="text-[10px] uppercase text-muted-foreground">{key}</div>
                <strong>{typeof value === "number" && value > 10000 ? formatCurrency(value) : String(value)}</strong>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Search className="h-4 w-4" />Similarity Search</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {similarity?.results?.map((r: any) => (
              <div key={r.entity_id} className="rounded-xl border bg-good-soft p-3 text-[12px]">
                <div className="flex items-center justify-between"><strong>{r.entity_name}</strong><Badge>{Math.round(r.similarity * 100)}%</Badge></div>
                <p className="mt-1 text-muted-foreground">{r.explanation}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><LineChart className="h-4 w-4" />Prediction Results</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3">
            {prediction?.predictions?.map((p: any) => (
              <div key={p.target} className="rounded-xl border bg-ai-soft p-3 text-[12px]">
                <div className="flex items-center justify-between"><strong>{p.target}</strong><Badge>{Math.round(p.confidence * 100)}%</Badge></div>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  <div>Baseline<br/><strong>{p.target === "agp_goal" ? `${p.baseline}%` : formatCurrency(p.baseline)}</strong></div>
                  <div>Predicted<br/><strong>{p.target === "agp_goal" ? `${p.predicted.toFixed(1)}%` : formatCurrency(p.predicted)}</strong></div>
                  <div>Delta<br/><strong>{p.target === "agp_goal" ? `${p.scenario_delta.toFixed(1)} pp` : formatCurrency(p.scenario_delta)}</strong></div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
