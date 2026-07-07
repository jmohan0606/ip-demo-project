"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { AiContentCard } from "@/components/patterns/ai-content-card";
import { DeltaIndicator } from "@/components/patterns/delta-indicator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { chartSeries, colors, type } from "@/styles/tokens";
import { formatCurrency } from "@/lib/utils";

/** Revenue Trend Explorer (CLAUDE.md 9.6). Self-contained: own dimension /
 * granularity / date-range controls, fetches /revenue/trend itself, follows the
 * shell's hierarchy scope. Every figure is Σ revenue_amount over real
 * transactions; the per-period driver summary is AI-generated from ONLY those
 * computed figures (see the endpoint's evidence block). */

interface TrendPeriod {
  period: string;
  total_revenue: number;
  prior_period: string | null;
  prior_revenue: number | null;
  change_pct: number | null;
  slices: Record<string, number>;
  top_slice: string | null;
  driver_summary: string;
  driver_bullets: string[];
}

interface TrendResponse {
  dimension: string;
  granularity: string;
  start: string;
  end: string;
  available_months: string[];
  slices: string[];
  periods: TrendPeriod[];
  evidence: { computation: string; transaction_count: number };
}

const DIMENSIONS = [
  { value: "division", label: "Division" },
  { value: "region", label: "Region" },
  { value: "market", label: "Market" },
  { value: "branch", label: "Branch" },
  { value: "advisor", label: "Advisor" },
  { value: "business_line", label: "Business Line" },
] as const;

const OTHER_COLOR = "#94A3B8"; // muted slate — reserved for the residual "Other" slice
const selectCls = "h-8 rounded-lg border border-border bg-background px-2 text-[12px]";

function sliceColor(label: string, index: number): string {
  return label === "Other" ? OTHER_COLOR : chartSeries[index % chartSeries.length];
}

export default function RevenueTrendExplorer() {
  const shell = useShellContext();
  const [dimension, setDimension] = useState<string>("division");
  const [granularity, setGranularity] = useState<"monthly" | "quarterly">("quarterly");
  const [start, setStart] = useState<string>("");
  const [end, setEnd] = useState<string>("");
  const [data, setData] = useState<TrendResponse | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        dimension,
        granularity,
        scope_type: shell.scopeType.toUpperCase(),
        scope_id: shell.scopeId,
      });
      if (start) params.set("start", start);
      if (end) params.set("end", end);
      const res = await apiClient.get<TrendResponse>(`/revenue/trend?${params.toString()}`);
      setData(res);
      setSelectedPeriod((prev) =>
        prev && res.periods.some((p) => p.period === prev) ? prev : res.periods[res.periods.length - 1]?.period ?? null,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load revenue trend");
    } finally {
      setBusy(false);
    }
    // refreshNonce in deps → the shell Refresh button re-fetches without losing controls.
  }, [dimension, granularity, start, end, shell.scopeType, shell.scopeId, shell.refreshNonce]);

  useEffect(() => {
    void load();
  }, [load]);

  const chartData = useMemo(
    () => (data?.periods ?? []).map((p) => ({ period: p.period, ...p.slices })),
    [data],
  );
  const selected = useMemo(
    () => data?.periods.find((p) => p.period === selectedPeriod) ?? data?.periods[data.periods.length - 1] ?? null,
    [data, selectedPeriod],
  );

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle className={type.cardTitle}>Revenue Trend Explorer</CardTitle>
            <p className="mt-0.5 text-[12px] text-muted-foreground">
              Revenue per period sliced by a selectable dimension, with AI-summarized drivers per period.
              Click a bar to inspect that period.
            </p>
          </div>
          {/* Controls — one row, above the chart */}
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Slice By
              <select className={selectCls} value={dimension} onChange={(e) => setDimension(e.target.value)}>
                {DIMENSIONS.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </label>
            <div className="flex overflow-hidden rounded-lg border border-border">
              {(["monthly", "quarterly"] as const).map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => setGranularity(g)}
                  className="h-8 px-2.5 text-[12px] font-medium capitalize"
                  style={
                    granularity === g
                      ? { backgroundColor: colors.primary, color: "#FFFFFF" }
                      : { color: colors.text.secondary }
                  }
                >
                  {g}
                </button>
              ))}
            </div>
            <label className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              From
              <select className={selectCls} value={start || data?.start || ""} onChange={(e) => setStart(e.target.value)}>
                {(data?.available_months ?? []).map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              To
              <select className={selectCls} value={end || data?.end || ""} onChange={(e) => setEnd(e.target.value)}>
                {(data?.available_months ?? []).map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-[12px] text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            {error}
          </div>
        ) : busy && !data ? (
          <div className="space-y-3">
            <div className="h-[320px] animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/60" />
            <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/60" />
          </div>
        ) : !data || data.periods.length === 0 ? (
          <div className="rounded-xl border border-dashed p-8 text-center text-[12px] text-muted-foreground" style={{ borderColor: colors.surface.border }}>
            No revenue transactions in the selected scope and date range.
          </div>
        ) : (
          <>
            <div className="h-[320px] w-full" style={{ opacity: busy ? 0.6 : 1 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
                  onClick={(state) => {
                    const label = (state as { activeLabel?: string } | null)?.activeLabel;
                    if (label) setSelectedPeriod(label);
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.18} vertical={false} />
                  <XAxis dataKey="period" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} />
                  <YAxis
                    tickFormatter={(v) => formatCurrency(Number(v), { compact: true })}
                    tickLine={false}
                    axisLine={false}
                    width={64}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    formatter={(value, name) => [formatCurrency(Number(value)), String(name)]}
                    labelStyle={{ fontWeight: 600, fontSize: 12 }}
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    cursor={{ fill: "rgba(37, 99, 235, 0.06)" }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} iconSize={10} />
                  {data.slices.map((label, i) => (
                    <Bar
                      key={label}
                      isAnimationActive={false}
                      dataKey={label}
                      stackId="revenue"
                      fill={sliceColor(label, i)}
                      stroke={colors.surface.card}
                      strokeWidth={1}
                      maxBarSize={44}
                      className="cursor-pointer"
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>

            {selected ? (
              <AiContentCard
                title={`Period Drivers — ${selected.period}`}
                footer={
                  <p className="text-[11px] text-muted-foreground">
                    Evidence: {data.evidence.computation} · {data.evidence.transaction_count.toLocaleString()} transactions
                  </p>
                }
              >
                <div className="flex flex-wrap items-start gap-4">
                  <div className="min-w-[180px]">
                    <div className={type.label} style={{ color: colors.text.muted }}>Total Revenue</div>
                    <div className={type.kpiValue} style={{ color: colors.text.primary }}>
                      {formatCurrency(selected.total_revenue, { compact: true })}
                    </div>
                    {selected.change_pct != null ? (
                      <DeltaIndicator changePct={selected.change_pct} suffix={`vs ${selected.prior_period}`} />
                    ) : (
                      <span className="text-[11px] text-muted-foreground">No prior period in data</span>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className={type.body} style={{ color: colors.text.secondary }}>{selected.driver_summary}</p>
                    {(selected.driver_bullets ?? []).length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {selected.driver_bullets.map((b, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-[12px]" style={{ color: colors.text.secondary }}>
                            <span className="mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: colors.primary }} />
                            <span className="tabular-nums">{b}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                      {data.slices.map((label, i) =>
                        selected.slices[label] ? (
                          <span key={label} className="inline-flex items-center gap-1.5 text-[12px] tabular-nums" style={{ color: colors.text.secondary }}>
                            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: sliceColor(label, i) }} />
                            {label}: <span className="font-semibold" style={{ color: colors.text.primary }}>{formatCurrency(selected.slices[label], { compact: true })}</span>
                          </span>
                        ) : null,
                      )}
                    </div>
                  </div>
                </div>
              </AiContentCard>
            ) : null}

            {/* Per-period breakdown — one entry per month/quarter across the WHOLE
                selected range, each with concise, exact-figure bullets (period-over-
                period change, leader, biggest movers). */}
            <div>
              <div className="mb-1.5 flex items-baseline justify-between">
                <h3 className="text-[12px] font-semibold uppercase tracking-[0.08em]" style={{ color: colors.text.muted }}>
                  {granularity === "quarterly" ? "Quarter-by-Quarter" : "Month-by-Month"} Breakdown ({data.periods.length} periods)
                </h3>
                <span className="text-[11px] text-muted-foreground">Newest first · click a period to inspect it above</span>
              </div>
              <div className="max-h-[26rem] space-y-2 overflow-y-auto pr-1">
                {[...data.periods].reverse().map((p) => (
                  <button
                    key={p.period}
                    type="button"
                    onClick={() => setSelectedPeriod(p.period)}
                    className={`block w-full rounded-xl border p-3 text-left transition-colors hover:bg-muted/40 ${
                      selectedPeriod === p.period ? "bg-muted/40" : ""
                    }`}
                    style={{ borderColor: selectedPeriod === p.period ? colors.primary : colors.surface.border }}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13px] font-bold" style={{ color: colors.text.primary }}>{p.period}</span>
                      <span className="text-[12px] font-semibold tabular-nums" style={{ color: colors.text.secondary }}>
                        {formatCurrency(p.total_revenue, { compact: true })}
                      </span>
                      {p.change_pct != null ? (
                        <DeltaIndicator changePct={p.change_pct} suffix={`vs ${p.prior_period}`} />
                      ) : (
                        <span className="text-[11px] text-muted-foreground">first period in data</span>
                      )}
                    </div>
                    <ul className="mt-1.5 space-y-0.5">
                      {(p.driver_bullets ?? []).map((b, i) => (
                        <li key={i} className="flex items-start gap-1.5 text-[12px]" style={{ color: colors.text.secondary }}>
                          <span className="mt-[5px] h-1 w-1 shrink-0 rounded-full" style={{ backgroundColor: colors.text.muted }} />
                          <span className="tabular-nums">{b}</span>
                        </li>
                      ))}
                    </ul>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
