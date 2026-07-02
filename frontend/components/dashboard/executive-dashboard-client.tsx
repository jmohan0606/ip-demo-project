"use client";

import { useEffect, useState } from "react";
import { DollarSign, LineChart, PiggyBank, TrendingUp } from "lucide-react";
import { fetchExecutiveDashboard } from "@/lib/api/dashboard";
import type { ExecutiveDashboardPayload } from "@/lib/types/dashboard";
import { KpiCard } from "@/components/cards/kpi-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RevenueTrendChart } from "@/components/charts/revenue-trend-chart";
import { ProductMixChart } from "@/components/charts/product-mix-chart";
import { InsightsCoachingPanel } from "@/components/dashboard/insights-coaching-panel";
import { PerformerTable } from "@/components/dashboard/performer-table";
import { ExecutiveDashboardSkeleton } from "@/components/dashboard/executive-dashboard-skeleton";

const iconMap = [DollarSign, PiggyBank, TrendingUp, LineChart];

export function ExecutiveDashboardClient() {
  const [data, setData] = useState<ExecutiveDashboardPayload | null>(null);

  useEffect(() => {
    fetchExecutiveDashboard().then(setData);
  }, []);

  if (!data) return <ExecutiveDashboardSkeleton />;

  return (
    <div className="animate-slide-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Badge variant="glass">Executive intelligence cockpit</Badge>
          <h2 className="mt-3 text-3xl font-black tracking-tight">Performance, Coaching & Revenue Intelligence</h2>
          <p className="mt-2 text-muted-foreground">
            {data.scopeLabel} · {data.periodLabel} · evidence-backed insight cards and recommendation actions.
          </p>
        </div>
        <div className="flex gap-2">
          <Badge variant="success">AI Reasoning Enabled</Badge>
          <Badge variant="warning">AGP Watchlist Active</Badge>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {data.kpis.map((kpi, index) => (
          <KpiCard
            key={kpi.id}
            label={kpi.label}
            value={kpi.value}
            change={kpi.change}
            icon={iconMap[index] ?? DollarSign}
            variant={kpi.tone}
          />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_.75fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Revenue Trend</CardTitle>
                <CardDescription>Monthly revenue trend with scope-aware filters.</CardDescription>
              </div>
              <Badge variant="glass">YTD / LTM</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <RevenueTrendChart data={data.performanceTrend} />
          </CardContent>
        </Card>

        <InsightsCoachingPanel insights={data.insights} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Product Revenue Mix</CardTitle>
            <CardDescription>Major category revenue contribution and growth signal.</CardDescription>
          </CardHeader>
          <CardContent>
            <ProductMixChart data={data.productMix} />
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <PerformerTable title="Top Performers" rows={data.topPerformers} />
          <PerformerTable title="Bottom Performers" rows={data.bottomPerformers} tone="risk" />
        </div>
      </div>
    </div>
  );
}
