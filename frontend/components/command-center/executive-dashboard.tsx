"use client";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Bar, BarChart, Cell, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  Building2, TrendingUp, TrendingDown, Users, Target, DollarSign, Wallet, PiggyBank,
  Layers, Gauge, ShieldAlert, AlertTriangle, MapPin, BarChart3, Sparkles, FileDown,
  PieChart, LineChart, Receipt, type LucideIcon,
} from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import {
  fetchScopeDashboard, fetchScopeAiInsight, type ScopeDashboard, type ScopeAiInsight,
  type DashboardTile,
} from "@/lib/api/scope";
import { WhyTrace } from "@/components/patterns/why-trace";
import { ScopeChildBars } from "@/components/charts/scope-child-bars";
import { AumNetflowWaterfall, type NetFlowStep } from "@/components/charts/aum-netflow-waterfall";
import { ScopeStatusDonut } from "@/components/charts/scope-status-donut";
import { RevenueTrendChart } from "@/components/charts/revenue-trend-chart";
import { RevenueDonut } from "@/components/charts/revenue-donut";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { PageHeader } from "@/components/patterns/page-header";
import { AiInsightSummary, type AiInsightData } from "@/components/patterns/ai-insight-summary";
import { AiCoachingCard, type AiCoachingData } from "@/components/patterns/ai-coaching-card";
import { DeltaIndicator } from "@/components/patterns/delta-indicator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiClient, downloadFile } from "@/lib/api/client";
import { useEntityLabel } from "@/lib/hooks/use-entity-label";
import { formatEntity } from "@/lib/utils";
import { colors } from "@/styles/tokens";
import type { ScopeType } from "@/lib/types/navigation";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

const CHILD_LABEL: Record<string, string> = {
  Firm: "Divisions", Division: "Regions", Region: "Markets", Market: "Advisors",
};

// tile.icon key → lucide icon + brand color (mockup: colored icon in a soft circle)
const TILE_ICON: Record<string, { icon: LucideIcon; color: string }> = {
  dollar: { icon: DollarSign, color: "#2563EB" },
  layers: { icon: Layers, color: "#4F46E5" },
  pie: { icon: PieChart, color: "#0D9488" },
  users: { icon: Users, color: "#F59E0B" },
  chart: { icon: LineChart, color: "#2563EB" },
  wallet: { icon: Wallet, color: "#14B8A6" },
  piggy: { icon: PiggyBank, color: "#14B8A6" },
  shield: { icon: ShieldAlert, color: "#F59E0B" },
  target: { icon: Target, color: "#0D9488" },
  gauge: { icon: Gauge, color: "#4F46E5" },
  alert: { icon: AlertTriangle, color: "#DC2626" },
};

const fmtTileValue = (t: DashboardTile): string => {
  if (t.value === null || t.value === undefined) return "—";
  if (t.unit === "usd") return compactUsd(Number(t.value));
  if (t.unit === "pct") return `${t.value}%`;
  return String(t.value);
};

const fmtPrior = (t: DashboardTile): string | undefined => {
  if (t.prior === null || t.prior === undefined) return undefined;
  const v = t.unit === "usd" ? compactUsd(Number(t.prior)) : t.unit === "pct" ? `${t.prior}%` : String(t.prior);
  return `${t.prior_label}: ${v}`;
};

/** Scope-aware KPI tiles straight from the payload (REQ-1): advisor persona gets
 * book-level tiles, leadership gets rollups — never a meaningless tile for the scope.
 * Each carries its REQ-2 trace (source + computation + drill-down link). */
function TileGrid({ tiles }: { tiles: DashboardTile[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {tiles.map((t) => {
        const ic = TILE_ICON[t.icon] ?? TILE_ICON.dollar;
        const inner = (
          <KpiStatCard
            label={t.label}
            value={fmtTileValue(t)}
            icon={ic.icon}
            iconColor={ic.color}
            changePct={t.delta_pct ?? undefined}
            positiveIsGood={t.positive_is_good}
            deltaSuffix={t.delta_unit === "pp" ? "pp" : undefined}
            priorLine={fmtPrior(t)}
            trace={t.trace}
          />
        );
        return t.id === "total_revenue"
          ? <div key={t.id} data-story-target="exec-kpi-revenue">{inner}</div>
          : <div key={t.id}>{inner}</div>;
      })}
    </div>
  );
}
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
                  <td className="px-3 py-2 font-medium">{formatEntity(a.advisor_id, a.advisor_name)}</td>
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
  const { label: entityLabel } = useEntityLabel();
  const [data, setData] = useState<ScopeDashboard | null>(null);
  const [netFlows, setNetFlows] = useState<{ available: boolean; steps: NetFlowStep[]; window?: { beginning_month: string; ending_month: string }; note?: string } | null>(null);
  const [ai, setAi] = useState<ScopeAiInsight | null>(null);
  const [coaching, setCoaching] = useState<{ insight: AiInsightData; coaching: AiCoachingData } | null>(null);
  const [busy, setBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [exporting, setExporting] = useState(false);

  const exportView = async (format: "pdf" | "pptx") => {
    setExporting(true);
    try {
      const st = shell.scopeType.toUpperCase();
      await downloadFile(
        `/export/dashboard?scope_type=${st}&scope_id=${shell.scopeId}&period=${shell.period}&compare_to=${encodeURIComponent(shell.compareTo)}&format=${format}`,
        `iperform_${st}_${shell.scopeId}_${shell.period}.${format}`.toLowerCase(),
      );
    } finally {
      setExporting(false);
    }
  };

  const isAdvisor = shell.scopeType === "Advisor";

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setData(await fetchScopeDashboard(shell.scopeType.toUpperCase(), shell.scopeId, shell.period, shell.compareTo));
      // AUM net-flows waterfall — leadership scopes only (not a single advisor).
      apiClient
        .get<{ available: boolean; steps: NetFlowStep[]; window?: { beginning_month: string; ending_month: string }; note?: string }>(
          `/scope/aum-net-flows?scope_type=${shell.scopeType.toUpperCase()}&scope_id=${shell.scopeId}&period=${shell.period}`)
        .then(setNetFlows)
        .catch(() => setNetFlows(null));
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
        // Advisor scope: the scope-level insight (narrative headline + GNN-peer-grounded
        // prose) for the Insight card, plus the advisor's own Coaching card (12.1).
        const [scopeInsight, advisorAi] = await Promise.all([
          fetchScopeAiInsight("ADVISOR", shell.scopeId, shell.period, shell.compareTo, shell.persona),
          apiClient.get<{ insight: AiInsightData; coaching: AiCoachingData }>(`/advisor/360/${shell.scopeId}/ai`),
        ]);
        setAi(scopeInsight);
        setCoaching(advisorAi);
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
  const insightData = ai?.insight ?? (isAdvisor ? coaching?.insight : undefined);

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow={<Badge variant="glass">Command Center · iPerform Insights and Coaching</Badge>}
        title={`${entityLabel(shell.scopeId)} Overview`}
        subtitle={
          <>
            {shell.scopeType} scope · {t?.advisor_count ?? "—"} advisors · {data?.period ?? shell.period} ·
            compare {data?.compare_to ?? shell.compareTo}. Every figure aggregated live from real per-advisor
            snapshots + transactions. Change scope/period/compare in the filter bar to re-roll the page.
          </>
        }
        actions={
          <>
            {busy && <span className="text-[12px] text-muted-foreground">Rolling up…</span>}
            <button
              onClick={() => void exportView("pdf")}
              disabled={exporting}
              className="inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-[12px] font-semibold disabled:opacity-50"
              title="Export this dashboard view to PDF (real data)"
            >
              <FileDown className="h-3.5 w-3.5" /> PDF
            </button>
            <button
              onClick={() => void exportView("pptx")}
              disabled={exporting}
              className="inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-[12px] font-semibold disabled:opacity-50"
              title="Export this dashboard view to PowerPoint (real data)"
            >
              <FileDown className="h-3.5 w-3.5" /> PPT
            </button>
          </>
        }
      />

      {/* Scope-aware KPI tiles (REQ-1): the SET adapts to the persona/scope; every tile
          shows delta + vs-PY prior where a real prior exists, and its REQ-2 why-trace. */}
      {data?.tiles?.length ? <TileGrid tiles={data.tiles} /> : null}

      {/* AI Insight Summary (grounded in this scope+period) + AI Coaching (Advisor scope only) */}
      <div className={`grid gap-3 ${isAdvisor ? "xl:grid-cols-2" : ""}`}>
        {insightData ? (
          <AiInsightSummary data={insightData} title={`AI Insight Summary — ${entityLabel(shell.scopeId)}`} />
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
              <RevenueTrendChart
                data={data.revenue.monthly_trend.map((m) => ({ period: m.month, revenue: m.revenue, aum: 0, nnm: 0, ncf: 0 }))}
                prior={data.revenue.monthly_trend_prior?.length === data.revenue.monthly_trend.length
                  ? data.revenue.monthly_trend_prior.map((m) => m.revenue) : undefined}
              />
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
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Gauge className="h-4 w-4 text-primary" /> Benchmarking vs Peers
              {data?.benchmark.why && (
                <WhyTrace trace={{
                  source: data.benchmark.model
                    ? `GNN similarity engine (${data.benchmark.model}) — embeddings learned over the real graph`
                    : "sibling scopes under the same parent, revenue-per-advisor from real snapshots",
                  computation: data.benchmark.why,
                  link: "/peer-benchmarking",
                  linkLabel: "Open Peer Benchmarking",
                }} />
              )}
            </CardTitle>
            <span className="flex items-center gap-2">
              {data?.benchmark.model && <Badge variant="glass">{data.benchmark.model}</Badge>}
              {data?.benchmark.percentile != null && <Badge variant="glass">{data.benchmark.percentile}th pctile</Badge>}
            </span>
          </CardHeader>
          <CardContent className="p-3">
            {isAdvisor && data?.benchmark.metrics?.length ? (
              <>
                {/* GNN peer group: WHO the peers are and WHY (REQ-2) */}
                <div className="mb-2 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">GNN peer group</span>
                  {(data.benchmark.peers ?? []).map((p) => (
                    <button
                      key={p.advisor_id}
                      onClick={() => shell.setScope("Advisor", p.advisor_id, p.advisor_name)}
                      title={`Embedding cosine similarity ${p.score}${p.market ? ` · ${p.market}` : ""} — click to view`}
                      className="rounded-full border bg-slate-50 px-2 py-0.5 text-[11px] font-medium hover:bg-slate-100"
                    >
                      {p.advisor_name} <span className="font-mono text-teal-700">{p.score.toFixed(2)}</span>
                    </button>
                  ))}
                </div>
                <table className="w-full text-[12px]">
                  <thead>
                    <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                      <th className="px-2 py-1.5">Metric</th>
                      <th className="px-2 py-1.5 text-right">You</th>
                      <th className="px-2 py-1.5 text-right">Peer Avg</th>
                      <th className="px-2 py-1.5 text-right">vs Peer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.benchmark.metrics.map((m) => {
                      const good = m.vs_peer_pct != null && (m.positive_is_good ? m.vs_peer_pct >= 0 : m.vs_peer_pct <= 0);
                      const fmt = (v: number | null) =>
                        v == null ? "—" : m.unit === "usd" ? compactUsd(v) : m.unit === "pct" ? `${v}%` : String(v);
                      return (
                        <tr key={m.metric} className="border-b last:border-0">
                          <td className="px-2 py-1.5 font-medium">{m.metric}</td>
                          <td className="px-2 py-1.5 text-right font-mono">{fmt(m.you)}</td>
                          <td className="px-2 py-1.5 text-right font-mono text-muted-foreground">{fmt(m.peer_avg)}</td>
                          <td className="px-2 py-1.5 text-right">
                            {m.vs_peer_pct == null ? "—" : (
                              <span className={`font-semibold ${good ? "text-teal-600" : "text-red-600"}`}>
                                {m.vs_peer_pct >= 0 ? "+" : ""}{m.vs_peer_pct}% {good ? "●" : "▲"}
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <p className="mt-2 text-[10px] leading-snug text-muted-foreground">{data.benchmark.why}</p>
              </>
            ) : data && data.benchmark.rows.length > 0 ? (
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
            ) : <div className="p-8 text-center text-[12px] text-muted-foreground">Computing peer group…</div>}
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

      {/* AUM Net-Flows waterfall (leadership scopes) — Beginning → New AUM → Departures
          → Market Growth → Fees → Ending, all real from /scope/aum-net-flows. */}
      {!isAdvisor && netFlows?.available && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <TrendingUp className="h-4 w-4 text-primary" /> AUM Net-Flows Bridge
            </CardTitle>
            {netFlows.window && (
              <span className="text-[10px] text-muted-foreground">
                {netFlows.window.beginning_month} → {netFlows.window.ending_month}
              </span>
            )}
          </CardHeader>
          <CardContent className="p-3">
            <AumNetflowWaterfall steps={netFlows.steps} />
            {netFlows.note && <p className="mt-1 text-[10px] text-muted-foreground">{netFlows.note}</p>}
          </CardContent>
        </Card>
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
          <div data-story-target="bottom-advisors">
            <AdvisorTable title="Bottom Advisors" icon={<TrendingDown className="h-4 w-4 text-red-600" />} rows={data?.bottom_advisors ?? []} onSelect={shell.setScope} />
          </div>
        </div>
      )}

      {/* Recent Transaction Highlights (mockup bottom-left): the latest REAL revenue
          transactions in scope, traversed txn→household / txn→product. */}
      {data && data.recent_transactions?.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Receipt className="h-4 w-4 text-primary" /> Recent Transaction Highlights
              <WhyTrace trace={{
                source: "phx_dm_revenue_transaction vertices, joined by transaction_for_household / transaction_for_product edge traversal",
                computation: "Latest real transactions for the advisors in this scope, newest first (largest movers break ties). These are the same rows every revenue figure on this page is summed from.",
                link: "/revenue-analytics",
                linkLabel: "Open Revenue Analytics",
              }} />
            </CardTitle>
            <a href="/revenue-analytics" className="text-[11px] font-semibold text-primary hover:underline">View All →</a>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Household</th>
                    {!isAdvisor && <th className="px-3 py-2">Advisor</th>}
                    <th className="px-3 py-2">Product</th>
                    <th className="px-3 py-2 text-right">Revenue Impact</th>
                    <th className="px-3 py-2">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_transactions.map((tx) => (
                    <tr key={tx.transaction_id} className="border-b last:border-0">
                      <td className="px-3 py-2 text-muted-foreground">{tx.date}</td>
                      <td className="px-3 py-2 font-medium text-primary">{tx.household ?? "—"}</td>
                      {!isAdvisor && <td className="px-3 py-2">{tx.advisor_name}</td>}
                      <td className="px-3 py-2">{tx.product ?? "—"}</td>
                      <td className={`px-3 py-2 text-right font-mono font-semibold ${tx.revenue_impact >= 0 ? "text-teal-600" : "text-red-600"}`}>
                        {tx.revenue_impact >= 0 ? "+" : "−"}${Math.abs(tx.revenue_impact).toLocaleString()}
                      </td>
                      <td className="px-3 py-2"><Badge variant="glass">{tx.type}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {data && (
        <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Evidence · </span>
          {data.evidence.source}. {data.evidence.advisor_ids_resolved} advisors resolved under {data.scope_type} {entityLabel(data.scope_id)}
          {" "}(sample {data.evidence.advisor_ids_sample.slice(0, 5).join(", ")}). ƒ {data.evidence.computation}
        </div>
      )}
    </div>
  );
}
