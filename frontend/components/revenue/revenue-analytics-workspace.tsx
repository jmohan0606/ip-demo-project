"use client";
import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { LineChart as LineIcon, PieChart as PieIcon, BarChart3 } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { colors, chartSeries, type } from "@/styles/tokens";
import type { ScopeType } from "@/lib/types/navigation";

interface RevenueAnalytics {
  scope_type: string;
  scope_id: string;
  kpis: {
    total_revenue: number;
    transaction_count: number;
    advisor_count: number;
    avg_revenue_per_advisor: number;
    months_covered: number;
    top_channel: string | null;
  };
  monthly_trend: Array<{ month: string; revenue: number }>;
  by_channel: Array<{ channel: string; revenue: number }>;
  by_child: Array<{ scope_type: string; scope_id: string; label: string; revenue: number; advisor_count: number }>;
  evidence: { source: string; advisor_ids_resolved: number; computation: string };
}

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

const CHILD_LABEL: Record<string, string> = {
  Firm: "Division", Division: "Region", Region: "Market", Market: "Advisor",
};

export function RevenueAnalyticsWorkspace() {
  const shell = useShellContext();
  const [data, setData] = useState<RevenueAnalytics | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setData(
        await apiClient.get<RevenueAnalytics>(
          `/revenue/analytics?scope_type=${shell.scopeType.toUpperCase()}&scope_id=${encodeURIComponent(shell.scopeId)}&period=${encodeURIComponent(shell.period)}`,
        ),
      );
    } finally {
      setBusy(false);
    }
  }, [shell.scopeType, shell.scopeId, shell.period]);

  useEffect(() => {
    void load();
  }, [load]);

  const k = data?.kpis;
  const channelTotal = (data?.by_channel ?? []).reduce((s, c) => s + c.revenue, 0) || 1;
  const childHeading = CHILD_LABEL[shell.scopeType] ?? "Sub-scope";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Revenue Intelligence</Badge>
          <h2 className="mt-2 text-[22px] font-black">{shell.scopeLabel || shell.scopeId} Revenue</h2>
          <p className="text-[12px] text-muted-foreground">
            {shell.scopeType} scope · {k?.transaction_count ?? "—"} transactions — trend, channel mix and
            breakdown computed from real revenue_transaction records. Scope-aware via the breadcrumb.
          </p>
        </div>
        {busy && <span className="text-[12px] text-muted-foreground">Loading…</span>}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Total Revenue" value={k ? compactUsd(k.total_revenue) : "—"} />
        <KpiStatCard label="Transactions" value={k ? k.transaction_count.toLocaleString() : "—"} />
        <KpiStatCard label="Avg / Advisor" value={k ? compactUsd(k.avg_revenue_per_advisor) : "—"} />
        <KpiStatCard label="Top Channel" value={k?.top_channel ?? "—"} />
      </div>

      <Card>
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <LineIcon className="h-4 w-4 text-primary" /> Revenue Trend · {k?.months_covered ?? 0} months
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data?.monthly_trend ?? []} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <defs>
                  <linearGradient id="revGrad" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor={colors.primary} stopOpacity={0.35} />
                    <stop offset="95%" stopColor={colors.primary} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 10, fill: colors.text.muted }}
                  tickLine={false}
                  axisLine={{ stroke: colors.surface.border }}
                  minTickGap={24}
                />
                <YAxis
                  tickFormatter={compactUsd}
                  tick={{ fontSize: 10, fill: colors.text.muted }}
                  tickLine={false}
                  axisLine={false}
                  width={48}
                />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
                  formatter={(v: number) => [compactUsd(v), "Revenue"]}
                />
                <Area type="monotone" dataKey="revenue" stroke={colors.primary} strokeWidth={2.5} fill="url(#revGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 xl:grid-cols-2">
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <PieIcon className="h-4 w-4 text-primary" /> Revenue by Channel
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3">
            <div className="flex items-center gap-3">
              <div className="h-[180px] w-[180px] shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data?.by_channel ?? []}
                      dataKey="revenue"
                      nameKey="channel"
                      innerRadius={52}
                      outerRadius={82}
                      paddingAngle={2}
                      stroke={colors.surface.card}
                      strokeWidth={2}
                    >
                      {(data?.by_channel ?? []).map((c, i) => (
                        <Cell key={c.channel} fill={chartSeries[i % chartSeries.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
                      formatter={(v: number, n: string) => [`${compactUsd(v)} · ${((v / channelTotal) * 100).toFixed(0)}%`, n]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="min-w-0 flex-1 space-y-1.5">
                {(data?.by_channel ?? []).map((c, i) => (
                  <li key={c.channel} className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: chartSeries[i % chartSeries.length] }} />
                    <span className={`flex-1 ${type.data}`} style={{ color: colors.text.secondary }}>{c.channel}</span>
                    <span className={`font-mono ${type.data}`} style={{ color: colors.text.primary }}>{compactUsd(c.revenue)}</span>
                    <span className={`w-9 text-right font-mono ${type.data}`} style={{ color: colors.text.muted }}>
                      {((c.revenue / channelTotal) * 100).toFixed(0)}%
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <BarChart3 className="h-4 w-4 text-primary" /> Revenue by {childHeading}
            </CardTitle>
            {data && data.by_child.length > 0 && <span className="text-[10px] text-muted-foreground">click to drill in</span>}
          </CardHeader>
          <CardContent className="p-3">
            {data && data.by_child.length > 0 ? (
              <div className="h-[220px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.by_child} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
                    <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
                    <XAxis dataKey="label" tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={{ stroke: colors.surface.border }} interval={0} angle={data.by_child.length > 6 ? -20 : 0} textAnchor={data.by_child.length > 6 ? "end" : "middle"} height={data.by_child.length > 6 ? 48 : 24} />
                    <YAxis tickFormatter={compactUsd} tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={false} width={48} />
                    <Tooltip cursor={{ fill: colors.surface.border, fillOpacity: 0.25 }} contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }} formatter={(v: number) => [compactUsd(v), "Revenue"]} />
                    <Bar dataKey="revenue" radius={[6, 6, 0, 0]} maxBarSize={64} cursor="pointer" onClick={(bar: unknown) => { const c = (bar as { payload?: RevenueAnalytics["by_child"][number] }).payload; if (c) shell.setScope(c.scope_type as ScopeType, c.scope_id, c.label); }}>
                      {data.by_child.map((c) => <Cell key={c.scope_id} fill={colors.primary} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="p-8 text-center text-[12px] text-muted-foreground">
                Advisor scope — no sub-breakdown. Channel mix and trend above are this advisor&apos;s own revenue.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {data && (
        <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Evidence · </span>
          {data.evidence.source}. {data.evidence.advisor_ids_resolved} advisors resolved under {data.scope_type}{" "}
          {data.scope_id}. ƒ {data.evidence.computation}
        </div>
      )}
    </div>
  );
}
