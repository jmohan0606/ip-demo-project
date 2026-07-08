"use client";
import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  BarChart3,
  Building2,
  DollarSign,
  Layers,
  LineChart as LineIcon,
  MapPin,
  Users,
} from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { RevenueDonut } from "@/components/charts/revenue-donut";
import { RevenueStateMap } from "@/components/charts/revenue-state-map";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { colors, type } from "@/styles/tokens";
import { formatCurrency } from "@/lib/utils";
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
    top_business_line: string | null;
    period: string;
  };
  comparison: { prior_revenue: number | null; change_pct: number | null; basis: string };
  monthly_trend: Array<{ month: string; revenue: number }>;
  by_channel: Array<{ channel: string; revenue: number }>;
  by_business_line: Array<{ category: string; revenue: number }>;
  by_geography: Array<{ state: string; revenue: number; advisor_count: number }>;
  by_child: Array<{ scope_type: string; scope_id: string; label: string; revenue: number; advisor_count: number }>;
  evidence: { source: string; advisor_ids_resolved: number; computation: string };
}

const CHILD_LABEL: Record<string, string> = {
  Firm: "Division", Division: "Region", Region: "Market", Market: "Advisor",
};

const fmtC = (v: number) => formatCurrency(v, { compact: true });

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
    // refreshNonce in deps → the shell Refresh button re-fetches this page without losing scope.
  }, [shell.scopeType, shell.scopeId, shell.period, shell.refreshNonce]);

  useEffect(() => {
    void load();
  }, [load]);

  const k = data?.kpis;
  const cmp = data?.comparison;
  const childHeading = CHILD_LABEL[shell.scopeType] ?? "Sub-scope";
  const periodLabel = k?.period && k.period !== "ALL" ? `${k.period} · ` : "";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Revenue Intelligence</Badge>
          <h2 className={`mt-2 ${type.pageTitle}`}>{shell.scopeLabel || shell.scopeId} Revenue</h2>
          <p className="text-[12px] text-muted-foreground">
            {shell.scopeType} scope · {periodLabel}{k?.transaction_count?.toLocaleString() ?? "—"} transactions — trend,
            channel, business-line and geographic mix computed from real revenue_transaction records. Scope-aware via the breadcrumb.
          </p>
        </div>
        {busy && <span className="text-[12px] text-muted-foreground">Loading…</span>}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div data-story-target="revenue-kpi-total">
        <KpiStatCard
          label="Total Revenue"
          value={k ? formatCurrency(k.total_revenue, { compact: true }) : "—"}
          icon={DollarSign}
          iconColor={colors.primary}
          changePct={cmp?.change_pct ?? undefined}
          deltaSuffix={cmp?.change_pct != null ? "vs prior yr" : undefined}
          trace={{ source: "phx_dm_revenue_transaction vertices via transaction_for_advisor edge traversal",
                   computation: "Σ revenue_amount over in-scope advisors in the selected period window; YoY delta vs the real month-shifted −12 window",
                   link: "/graph-explorer" }}
        />
        </div>
        <KpiStatCard label="Transactions" value={k ? k.transaction_count.toLocaleString() : "—"} icon={Activity} iconColor={colors.aiAccent}
          trace={{ source: "same transaction traversal as Total Revenue",
                   computation: "count of real transaction records kept in the selected period window — every chart on this page is summed from these rows" }} />
        <KpiStatCard label="Avg / Advisor" value={k ? formatCurrency(k.avg_revenue_per_advisor, { compact: true }) : "—"} icon={Users} iconColor={colors.positive}
          trace={{ source: "transaction traversal + hierarchy scope resolution",
                   computation: "period revenue ÷ advisors resolved under the selected scope" }} />
        <KpiStatCard label="Top Business Line" value={k?.top_business_line ?? "—"} icon={Layers} iconColor={colors.warning}
          trace={{ source: "product→subcategory→category graph mapping",
                   computation: "business line with the largest Σ revenue in the window (each transaction categorized by its product's real category edge)" }} />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <LineIcon className="h-4 w-4 text-primary" /> Revenue Trend · {k?.months_covered ?? 0} months
          </CardTitle>
          {cmp?.prior_revenue != null && (
            <span className="text-[11px] text-muted-foreground">
              Prior year {fmtC(cmp.prior_revenue)}
            </span>
          )}
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
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={{ stroke: colors.surface.border }} minTickGap={24} />
                <YAxis tickFormatter={fmtC} tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={false} width={48} />
                <Tooltip contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }} formatter={(v: number) => [fmtC(v), "Revenue"]} />
                <Area type="monotone" dataKey="revenue" stroke={colors.primary} strokeWidth={2.5} fill="url(#revGrad)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Three distinct breakdown dimensions (CLAUDE.md 9.12): Business Line (donut), Channel (bar), Region (map). */}
      <div className="grid gap-3 xl:grid-cols-2">
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Layers className="h-4 w-4 text-primary" /> Revenue by Business Line
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3">
            {data && data.by_business_line.length > 0 ? (
              <RevenueDonut
                data={data.by_business_line.map((b) => ({ label: b.category, value: b.revenue }))}
                centerLabel="Total"
              />
            ) : (
              <div className="p-8 text-center text-[12px] text-muted-foreground">No revenue in this period.</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <BarChart3 className="h-4 w-4 text-primary" /> Revenue by Channel
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3">
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.by_channel ?? []} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 12 }}>
                  <CartesianGrid horizontal={false} stroke={colors.surface.border} strokeOpacity={0.6} />
                  <XAxis type="number" tickFormatter={fmtC} tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={{ stroke: colors.surface.border }} />
                  <YAxis type="category" dataKey="channel" tick={{ fontSize: 10, fill: colors.text.secondary }} tickLine={false} axisLine={false} width={150} />
                  <Tooltip cursor={{ fill: colors.surface.border, fillOpacity: 0.25 }} contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }} formatter={(v: number) => [fmtC(v), "Revenue"]} />
                  <Bar dataKey="revenue" radius={[0, 6, 6, 0]} maxBarSize={26} isAnimationActive={false}>
                    {(data?.by_channel ?? []).map((c) => <Cell key={c.channel} fill={colors.primary} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <MapPin className="h-4 w-4 text-primary" /> Revenue by Region · Geographic Distribution
          </CardTitle>
          <span className="text-[10px] text-muted-foreground">by branch state · advisor_in_branch → branch.state</span>
        </CardHeader>
        <CardContent className="p-3">
          {data && data.by_geography.length > 0 ? (
            <RevenueStateMap data={data.by_geography} />
          ) : (
            <div className="p-8 text-center text-[12px] text-muted-foreground">No geographic revenue in this period.</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <Building2 className="h-4 w-4 text-primary" /> Revenue by {childHeading}
          </CardTitle>
          {data && data.by_child.length > 0 && <span className="text-[10px] text-muted-foreground">click a bar to drill in</span>}
        </CardHeader>
        <CardContent className="p-3">
          {data && data.by_child.length > 0 ? (
            <div className="h-[240px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.by_child} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
                  <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
                  <XAxis dataKey="label" tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={{ stroke: colors.surface.border }} interval={0} angle={data.by_child.length > 6 ? -20 : 0} textAnchor={data.by_child.length > 6 ? "end" : "middle"} height={data.by_child.length > 6 ? 48 : 24} />
                  <YAxis tickFormatter={fmtC} tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={false} width={48} />
                  <Tooltip cursor={{ fill: colors.surface.border, fillOpacity: 0.25 }} contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }} formatter={(v: number) => [fmtC(v), "Revenue"]} />
                  <Bar dataKey="revenue" radius={[6, 6, 0, 0]} maxBarSize={64} isAnimationActive={false} cursor="pointer" onClick={(bar: unknown) => { const c = (bar as { payload?: RevenueAnalytics["by_child"][number] }).payload; if (c) shell.setScope(c.scope_type as ScopeType, c.scope_id, c.label); }}>
                    {data.by_child.map((c) => <Cell key={c.scope_id} fill={colors.primary} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="p-8 text-center text-[12px] text-muted-foreground">
              Advisor scope — no sub-breakdown. Channel, business-line and trend above are this advisor&apos;s own revenue.
            </div>
          )}
        </CardContent>
      </Card>

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
