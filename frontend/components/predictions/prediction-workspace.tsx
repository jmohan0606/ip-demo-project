"use client";

import { BrainCircuit, LineChart, Target, TrendingUp } from "lucide-react";
import { getForecastSeries, getPredictionDrivers, getPredictionModels } from "@/lib/api/predictions_workspace";
import { ForecastChart } from "@/components/predictions/forecast-chart";
import { PredictionModelCard } from "@/components/predictions/prediction-model-card";
import { PredictionDriversPanel } from "@/components/predictions/prediction-drivers-panel";
import { KpiCard } from "@/components/cards/kpi-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function PredictionWorkspace() {
  const forecast = getForecastSeries();
  const models = getPredictionModels();
  const drivers = getPredictionDrivers();

  return (
    <div className="animate-slide-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Badge variant="glass">Prediction & Forecasting</Badge>
          <h2 className="mt-3 text-3xl font-black tracking-tight">Revenue, NNM, AUM & Opportunity Forecasting</h2>
          <p className="mt-2 max-w-3xl text-muted-foreground">
            Forecast advisor outcomes using feature store signals, graph embeddings, GNN-ready features, CRM activity, AGP status and recommendation feedback.
          </p>
        </div>
        <Badge variant="success">Scikit-Learn + Graph/GNN Ready</Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Revenue Forecast Lift" value="+13.3%" change="+5.1%" icon={LineChart} />
        <KpiCard label="NNM Risk Score" value="Medium" change="-2.1%" icon={TrendingUp} variant="risk" />
        <KpiCard label="AGP Goal Probability" value="71%" change="+8.4%" icon={Target} variant="insight" />
        <KpiCard label="Opportunity Propensity" value="84%" change="+6.2%" icon={BrainCircuit} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>Revenue Forecast</CardTitle>
            <CardDescription>Baseline vs forecast with confidence band.</CardDescription>
          </CardHeader>
          <CardContent>
            <ForecastChart data={forecast} />
          </CardContent>
        </Card>

        <PredictionDriversPanel drivers={drivers} />
      </div>

      <div>
        <h3 className="mb-4 text-xl font-black">Prediction Models</h3>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {models.map((model) => <PredictionModelCard key={model.modelId} model={model} />)}
        </div>
      </div>

      <Card className="insight-gradient">
        <CardHeader>
          <CardTitle>Explainability Summary</CardTitle>
          <CardDescription>Why the prediction changed and how the result should be used.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <div>Revenue forecast is primarily lifted by managed revenue mix and CRM meeting cadence.</div>
          <div>NNM risk remains medium because outflows are concentrated in a small set of high-AUM households.</div>
          <div>GNN opportunity propensity uses graph relationships between advisor, households, accounts, products, opportunities and recommendation outcomes.</div>
          <div>Fallback behavior supports Scikit-Learn when XGBoost or graph-native models are unavailable.</div>
        </CardContent>
      </Card>
    </div>
  );
}
