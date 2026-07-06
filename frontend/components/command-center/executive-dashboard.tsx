"use client";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Bar, BarChart, Cell, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  Building2, TrendingUp, TrendingDown, Users, Target, DollarSign, Wallet, PiggyBank,
  Layers, Gauge, ShieldAlert, AlertTriangle, MapPin, BarChart3, Sparkles,
} from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import {
  fetchScopeDashboard, fetchScopeAiInsight, type ScopeDashboard, type ScopeAiInsight,
} from "@/lib/api/scope";
import { ScopeChildBars } from "@/components/charts/scope-child-bars";
import { ScopeStatusDonut } from "@/components/charts/scope-status-donut";
import { RevenueTrendChart } from "@/components/charts/revenue-trend-chart";
import { RevenueDonut } from "@/components/charts/revenue-donut";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { AiInsightSummary, type AiInsightData } from "@/components/patterns/ai-insight-summary";
import { AiCoachingCard, type AiCoachingData } from "@/components/patterns/ai-coaching-card";
import { DeltaIndicator } from "@/components/patterns/delta-indicator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api/client";
import { colors } from "@/styles/tokens";
import type { ScopeType } from "@/lib/types/navigation";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

const CHILD_LABEL: Record<string, string> = {
  Firm: "Divisions", Division: "Regions", Region: "Markets", Market: "Advisors",
};
const STATUS_STYLE: Record<string, "success" | "warning" | "destructive"> = {
  on_track: "success", attention: "warning", urgent: "warning", critical: "destructive",
};

function AdvisorTable({
  title, icon, rows, onSelect,
}: {
  title: string; icon: ReactNode;
  rows: import("@/lib/api/scope").ScopeTopAdvisor[];
  onSelect: (t: ScopeType, id: string, label: string) => void;
}) {
  return (
    <Card>
      <CardHeader className="p-3">
        <CardTitle className="flex items-center gap-2 text-[13px]">{icon} {title}</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                <th className="px-3 py-2">Advisor</th>
                <th className="px-3 py-2 text-right">Revenue (LTM)</th>
                <th className="px-3 py-2 text-right">AUM</th>
                <th className="px-3 py-2 text-right">Risk</th>
                <th className="px-3 py-2">Why</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.advisor_id} className="cursor-pointer border-b last:border-0 hover:bg-muted/40" onClick={() => onSelect("Advisor", a.advisor_id, a.advisor_name)}>
                  <td className="px-3 py-2 font-medium">{a.advisor_name}</td>
                  <td className="px-3 py-2 text-right font-mono">{compactUsd(a.revenue_ltm)}</td>
                  <td className="px-3 py-2 text-right font-mono text-muted-foreground">{compactUsd(a.aum_total)}</td>
                  <td className="px-3 py-2 text-right"><Badge variant={STATUS_STYLE[a.status] ?? "glass"}>{a.agp_risk_score ?? "—"}</Badge></td>
                  <td className="px-3 py-2 text-[11px] text-muted-foreground">{a.reason ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function MarketTable({ title, rows, tone }: { title: string; rows: import("@/lib/api/scope").MarketRow[]; tone: "up" | "down" }) {
  return (
    <Card>
      <CardHeader className="p-3">
        <CardTitle className="flex items-center gap-2 text-[13px]">
          <MapPin className="h-4 w-4" style={{ color: tone === "up" ? colors.positive : colors.negative }} /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
              <th className="px-3 py-2">Market</th>
              <th className="px-3 py-2 text-right">Revenue (LTM)</th>
              <th className="px-3 py-2 text-right">Advisors</th>
              <th className="px-3 py-2 text-right">Per Advisor</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.scope_id} className="border-b last:border-0">
                <td className="px-3 py-2 font-medium">{m.label}</td>
                <td className="px-3 py-2 text-right font-mono">{compactUsd(m.revenue_ltm)}</td>
                <td className="px-3 py-2 text-right text-muted-foreground">{m.advisor_count}</td>
                <td className="px-3 py-2 text-right font-mono text-muted-foreground">{compactUsd(m.rev_per_advisor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

export function ExecutiveDashboard() {
  const shell = useShellContext();
  const [data, setData] = useState<ScopeDashboard | null>(null);
  const [ai, setAi] = useState<ScopeAiInsight | null>(null);
  const [coaching, setCoaching] = useState<{ insight: AiInsightData; coaching: AiCoachingData } | null>(null);
  const [busy, setBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);

  const isAdvisor = shell.scopeType === "Advisor";

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setData(await fetchScopeDashboard(shell.scopeType.toUpperCase(), shell.scopeId, shell.period, shell.compareTo));
    } finally {
      setBusy(false);
    }
  }, [shell.scopeType, shell.scopeId, shell.period, shell.compareTo]);

  const loadAi = useCallback(async () => {
    setAiBusy(true);
    setAi(null);
    setCoaching(null);
    try {
      if (isAdvisor) {
        // Advisor scope: the advisor's own Insight + Coaching (coaching only shows here — 12.1).
        setCoaching(await apiClient.get(`/advisor/360/${shell.scopeId}/ai`));
      } else {
        setAi(await fetchScopeAiInsight(shell.scopeType.toUpperCase(), shell.scopeId, shell.period, shell.compareTo, shell.persona));
      }
    } catch {
      /* AI card stays hidden on failure — dashboard numbers already render. */
    } finally {
      setAiBusy(false);
    }
  }, [isAdvisor, shell.scopeType, shell.scopeId, shell.period, shell.compareTo, shell.persona]);

  useEffect(() => { void load(); }, [load, shell.refreshNonce]);
  useEffect(() => { void loadAi(); }, [loadAi, shell.refreshNonce]);

  const t = data?.totals;
  const head = data?.headline;
  const childHeading = CHILD_LABEL[shell.scopeType] ?? "Breakdown";
  const atRisk = t ? t.status_distribution.attention + t.status_distribution.urgent + t.status_distribution.critical : 0;
  const insightData = isAdvisor ? coaching?.insight : ai?.insight;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Command Center · iPerform Insights and Coaching</Badge>
          <h2 className="mt-2 text-[22px] font-black">{shell.scopeLabel || shell.scopeId} Overview</h2>
          <p className="text-[12px] text-muted-foreground">
            {shell.scopeType} scope · {t?.advisor_count ?? "—"} advisors · {data?.period ?? shell.period} ·
            compare {data?.compare_to ?? shell.compareTo}. Every figure aggregated live from real per-advisor
            snapshots + transactions. Change scope/period/compare in the filter bar to re-roll the page.
          </p>
        </div>
        {busy && <span className="text-[12px] text-muted-foreground">Rolling up…</span>}
      </div>

      {/* KPI grid — headline revenue is period-windowed; its delta respects Compare-To (12.1) */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Advisors In Scope" value={String(t?.advisor_count ?? "—")} icon={Users} iconColor="#2563EB" />
        <KpiStatCard
          label={`Revenue (${data?.period ?? shell.period})`}
          value={head ? compactUsd(head.revenue) : "—"}
          icon={DollarSign} iconColor="#2563EB"
          changePct={head?.delta_pct ?? undefined}
          deltaSuffix={`vs ${head?.compare_to ?? shell.compareTo}`}
        />
        <KpiStatCard label="AUM" value={t ? compactUsd(t.aum_total) : "—"} icon={Wallet} iconColor="#14B8A6" />
        <KpiStatCard label="NNM (Annualized)" value={t ? compactUsd(t.nnm_annualized) : "—"} icon={PiggyBank} iconColor="#14B8A6" />
        <KpiStatCard label="Managed Revenue" value={t ? compactUsd(t.managed_revenue) : "—"} icon={Layers} iconColor="#4F46E5" />
        <KpiStatCard label="Avg Goal Attainment" value={t ? `${t.avg_goal_attainment}%` : "—"} icon={Gauge} iconColor="#4F46E5" />
        <KpiStatCard label="Avg AGP Risk Score" value={t ? String(t.avg_agp_risk_score) : "—"} icon={ShieldAlert} iconColor="#F59E0B" positiveIsGood={false} />
        <KpiStatCard label="At-Risk Advisors" value={t ? String(atRisk) : "—"} icon={AlertTriangle} iconColor="#DC2626" />
      </div>

      {/* AI Insight Summary (grounded in this scope+period) + AI Coaching (Advisor scope only) */}
      <div className={`grid gap-3 ${isAdvisor ? "xl:grid-cols-2" : ""}`}>
        {insightData ? (
          <AiInsightSummary data={insightData} title={`AI Insight Summary — ${shell.scopeLabel || shell.scopeId}`} />
        ) : (
          <div className="flex h-[220px] items-center justify-center rounded-xl border bg-white text-[12px] text-muted-foreground">
            {aiBusy ? "Generating scope insight…" : "AI insight unavailable"}
          </div>
        )}
        {isAdvisor && coaching?.coaching && <AiCoachingCard data={coaching.coaching} />}
      </div>

      {/* AGP Program Status (non-advisor) */}
      {t && !isAdvisor && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]"><Target className="h-4 w-4 text-primary" /> AGP Program Status</CardTitle>
            <a href="/agp" className="text-[11px] font-semibold text-primary hover:underline">View Details →</a>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-4">
            <div className="rounded-lg border bg-teal-50 px-3 py-2"><div className="text-[10px] uppercase text-muted-foreground">On Track</div><div className="text-[18px] font-bold text-teal-700">{t.status_distribution.on_track}</div></div>
            <div className="rounded-lg border bg-amber-50 px-3 py-2"><div className="text-[10px] uppercase text-muted-foreground">Attention</div><div className="text-[18px] font-bold text-amber-700">{t.status_distribution.attention}</div></div>
            <div className="rounded-lg border bg-orange-50 px-3 py-2"><div className="text-[10px] uppercase text-muted-foreground">Urgent</div><div className="text-[18px] font-bold text-orange-700">{t.status_distribution.urgent}</div></div>
            <div className="rounded-lg border bg-red-50 px-3 py-2"><div className="text-[10px] uppercase text-muted-foreground">Critical</div><div className="text-[18px] font-bold text-red-700">{t.status_distribution.critical}</div></div>
          </CardContent>
        </Card>
      )}

      {/* Revenue Trend (period-windowed) + Revenue by Product Category */}
      <div className="grid gap-3 xl:grid-cols-[1.5fr_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]"><TrendingUp className="h-4 w-4 text-primary" /> Revenue Trend ({data?.period ?? shell.period})</CardTitle>
            {head?.delta_pct != null && <DeltaIndicator changePct={head.delta_pct} suffix={`vs ${head.compare_to}`} />}
          </CardHeader>
          <CardContent className="p-3">
            {data && data.revenue.monthly_trend.length > 0 ? (
              <RevenueTrendChart data={data.revenue.monthly_trend.map((m) => ({ period: m.month, revenue: m.revenue, aum: 0, nnm: 0, ncf: 0 }))} />
            ) : <div className="p-8 text-center text-[12px] text-muted-foreground">No revenue in this window.</div>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Layers className="h-4 w-4 text-primary" /> Revenue by Product Category</CardTitle></CardHeader>
          <CardContent className="p-3">
            {data && data.revenue.by_business_line.length > 0 ? (
              <RevenueDonut data={data.revenue.by_business_line.map((b) => ({ label: b.category, value: b.revenue }))} centerLabel={`Total (${data.period})`} />
            ) : <div className="p-8 text-center text-[12px] text-muted-foreground">No category data.</div>}
          </CardContent>
        </Card>
      </div>

      {/* Revenue Drivers vs Prior Year + Benchmarking vs Peers */}
      <div className="grid gap-3 xl:grid-cols-2">
        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><BarChart3 className="h-4 w-4 text-primary" /> Revenue Drivers vs Prior Year</CardTitle></CardHeader>
          <CardContent className="p-3">
            {data && data.revenue.revenue_drivers.length > 0 ? (
              <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.revenue.revenue_drivers.slice(0, 8)} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.18} horizontal={false} />
                    <XAxis type="number" tickFormatter={(v) => compactUsd(Number(v))} tick={{ fontSize: 10 }} />
                    <YAxis type="category" dataKey="category" width={110} tick={{ fontSize: 11 }} />
                    <ReferenceLine x={0} stroke={colors.text.muted} />
                    <Tooltip formatter={(v: number) => compactUsd(Number(v))} />
                    <Bar dataKey="change" radius={[0, 6, 6, 0]} isAnimationActive={false} minPointSize={2}>
                      {data.revenue.revenue_drivers.slice(0, 8).map((d) => (
                        <Cell key={d.category} fill={d.change >= 0 ? colors.positive : colors.negative} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <div className="p-8 text-center text-[12px] text-muted-foreground">Prior-year window not fully covered for this period — pick MTD/QTD/YTD/LTM to see YoY drivers.</div>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]"><Gauge className="h-4 w-4 text-primary" /> Benchmarking vs Peers</CardTitle>
            {data?.benchmark.percentile != null && <Badge variant="glass">{data.benchmark.percentile}th pctile</Badge>}
          </CardHeader>
          <CardContent className="p-3">
            {data && data.benchmark.rows.length > 0 ? (
              <>
                <div className="mb-2 text-[11px] text-muted-foreground">
                  Revenue per advisor across {data.benchmark.peer_type.toLowerCase()}s · firm avg{" "}
                  <span className="font-mono text-foreground">{compactUsd(data.benchmark.firm_per_advisor)}</span>
                  {data.benchmark.vs_firm_pct != null && <> · this scope <span className={data.benchmark.vs_firm_pct >= 0 ? "text-teal-600" : "text-red-600"}>{data.benchmark.vs_firm_pct >= 0 ? "+" : ""}{data.benchmark.vs_firm_pct}%</span></>}
                </div>
                <div className="h-[230px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.benchmark.rows} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.18} horizontal={false} />
                      <XAxis type="number" tickFormatter={(v) => compactUsd(Number(v))} tick={{ fontSize: 10 }} />
                      <YAxis type="category" dataKey="label" width={110} tick={{ fontSize: 11 }} />
                      <ReferenceLine x={data.benchmark.firm_per_advisor} stroke={colors.warning} strokeDasharray="4 3" label={{ value: "firm avg", fontSize: 9, fill: colors.warning, position: "top" }} />
                      <Tooltip formatter={(v: number) => compactUsd(Number(v))} />
                      <Bar dataKey="per_advisor" radius={[0, 6, 6, 0]} isAnimationActive={false} minPointSize={2}>
                        {data.benchmark.rows.map((r) => (
                          <Cell key={r.scope_id} fill={r.is_current ? colors.primary : "#60A5FA"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </>
            ) : <div className="p-8 text-center text-[12px] text-muted-foreground">No peer group at this scope.</div>}
          </CardContent>
        </Card>
      </div>

      {/* Revenue by child scope + Advisor status mix (non-advisor) */}
      {!isAdvisor && (
        <div className="grid gap-3 xl:grid-cols-[1.5fr_1fr]">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between p-3">
              <CardTitle className="flex items-center gap-2 text-[13px]"><Building2 className="h-4 w-4 text-primary" /> Revenue by {childHeading}</CardTitle>
              <span className="text-[10px] text-muted-foreground">click a bar to drill in</span>
            </CardHeader>
            <CardContent className="p-3">
              {data && data.child_breakdown.length > 0 ? (
                <ScopeChildBars data={data.child_breakdown} onSelect={(c) => shell.setScope(c.scope_type as ScopeType, c.scope_id, c.label)} />
              ) : <div className="p-8 text-center text-[12px] text-muted-foreground">No sub-scopes.</div>}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Target className="h-4 w-4 text-primary" /> Advisor Status Mix</CardTitle></CardHeader>
            <CardContent className="p-3">{t && <ScopeStatusDonut data={t.status_distribution} />}</CardContent>
          </Card>
        </div>
      )}

      {/* Top & Bottom Markets (non-advisor, non-market) */}
      {!isAdvisor && data && (data.markets.top.length > 0) && (
        <div className="grid gap-3 xl:grid-cols-2">
          <MarketTable title="Top Markets" rows={data.markets.top} tone="up" />
          {data.markets.bottom.length > 0 && <MarketTable title="Bottom Markets" rows={data.markets.bottom} tone="down" />}
        </div>
      )}

      {/* Top & Bottom Advisors */}
      {!isAdvisor && (
        <div className="grid gap-3 xl:grid-cols-2">
          <AdvisorTable title="Top Advisors" icon={<TrendingUp className="h-4 w-4 text-teal-600" />} rows={data?.top_advisors ?? []} onSelect={shell.setScope} />
          <AdvisorTable title="Bottom Advisors" icon={<TrendingDown className="h-4 w-4 text-red-600" />} rows={data?.bottom_advisors ?? []} onSelect={shell.setScope} />
        </div>
      )}

      {data && (
        <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Evidence · </span>
          {data.evidence.source}. {data.evidence.advisor_ids_resolved} advisors resolved under {data.scope_type} {data.scope_id}
          {" "}(sample {data.evidence.advisor_ids_sample.slice(0, 5).join(", ")}). ƒ {data.evidence.computation}
        </div>
      )}
    </div>
  );
}
