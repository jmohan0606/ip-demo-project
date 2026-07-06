"use client";

/**
 * Learning State Showcase (CLAUDE.md 9.5 — Opportunities & Recommendations).
 * A client-legible explanation of the RL feedback loop in three beats:
 *  (a) what each feedback action does to ranking (real ACTION_SIGNALS),
 *  (b) family weights moving round-by-round across the replayed feedback loop,
 *  (c) baseline -> learned weight per family with the events that drove it.
 * Every number comes from GET /feedback-learning/impact-trend — no fabricated series.
 */

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { chartSeries, colors, type } from "@/styles/tokens";

interface ActionSignal {
  reward: number;
  delta: number;
  summary: string;
}

interface TrendRound {
  round: number;
  advisor_id: string;
  action: string;
  action_family: string;
  cumulative_reward: number;
  weights: Record<string, number>;
}

interface BaselineVsLearned {
  family: string;
  baseline_weight: number;
  neutral_weight: number;
  learned_weight: number;
  change: number;
  positive_events: number;
  negative_events: number;
  by_action: Record<string, number>;
}

interface ImpactTrendResponse {
  advisor_ids: string[];
  event_count: number;
  families: string[];
  trend: TrendRound[];
  baseline_vs_learned: BaselineVsLearned[];
  action_signals: Record<string, ActionSignal>;
  totals: { cumulative_reward: number; captured_impact: number };
  bandit?: BanditSpec;
  note: string;
}

interface BanditSpec {
  formalism: string;
  state: { description: string; source: string };
  actions: { description: string; arms: string };
  reward: { description: string; base_reward_by_action: Record<string, number>; outcome_adjustment: Record<string, number>; clamp: string };
  policy: { description: string; formula: string };
  update_rule: { description: string; formula: string; neutral_weight: number; delta_by_action: Record<string, number> };
  exploration: string;
  note: string;
}

// Fixed action display order: strongest positive -> strongest negative.
const ACTION_ORDER = ["COMPLETE", "ACCEPT", "MODIFY", "IGNORE", "REJECT"] as const;

function familyLabel(family: string): string {
  return family
    .split("_")
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}

function familyColor(families: string[], family: string): string {
  const idx = families.indexOf(family);
  return chartSeries[idx >= 0 ? idx % chartSeries.length : 0];
}

function takeaway(row: BaselineVsLearned): string {
  const label = familyLabel(row.family);
  const pct = Math.abs(Math.round((row.learned_weight / Math.max(row.baseline_weight, 0.0001) - 1) * 100));
  if (row.change > 0.005) {
    const completes = row.by_action["COMPLETE"] || 0;
    const verb = completes > 0 ? "completing" : "accepting";
    return `Advisors kept ${verb} ${label} actions (${row.positive_events} positive signals), so the system now ranks them ~${pct}% higher.`;
  }
  if (row.change < -0.005) {
    const rejects = row.by_action["REJECT"] || 0;
    const verb = rejects > 0 ? "rejecting" : "ignoring";
    return `Advisors kept ${verb} ${label} actions (${row.negative_events} negative signals), so the system now ranks them ~${pct}% lower.`;
  }
  return `Feedback on ${label} actions was mixed — the system left its ranking unchanged.`;
}

export default function LearningStateShowcase() {
  const [data, setData] = useState<ImpactTrendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiClient
      .get<ImpactTrendResponse>("/feedback-learning/impact-trend")
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load learning state");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Flatten per-round weight snapshots into Recharts rows: { round, <family>: weight }.
  const chartData = useMemo(() => {
    if (!data) return [];
    return data.trend.map((r) => ({
      round: r.round,
      action: r.action,
      action_family: r.action_family,
      ...r.weights,
    }));
  }, [data]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className={type.cardTitle}>How the System Gets Smarter</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 w-2/3 animate-pulse rounded bg-slate-200" />
            <div className="h-[240px] w-full animate-pulse rounded-lg bg-slate-100" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-slate-200" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data || data.trend.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className={type.cardTitle}>How the System Gets Smarter</CardTitle>
        </CardHeader>
        <CardContent>
          <p className={type.body} style={{ color: colors.text.secondary }}>
            {error
              ? `Learning-state data unavailable: ${error}`
              : "No feedback events recorded yet — accept, complete, or reject a recommendation to start the learning loop."}
          </p>
        </CardContent>
      </Card>
    );
  }

  const families = data.families;
  const signals = ACTION_ORDER.filter((a) => a in data.action_signals).map((a) => ({
    action: a,
    ...data.action_signals[a],
  }));

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <span
            className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
            style={{ backgroundColor: colors.aiAccent }}
          >
            Learning Loop
          </span>
          <CardTitle className={type.cardTitle}>How the System Gets Smarter</CardTitle>
        </div>
        <p className={type.data} style={{ color: colors.text.muted }}>
          Replay of {data.event_count} real feedback events across {data.advisor_ids.length} advisors
          {" · "}cumulative reward {data.totals.cumulative_reward.toFixed(1)}
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* (0) Formal contextual-bandit framing of the loop (Section 11.2) */}
        {data.bandit ? (
          <div className="rounded-lg border p-3" style={{ borderColor: colors.surface.border, background: "#F8FAFC" }}>
            <div className={type.label} style={{ color: colors.text.secondary }}>
              Formalism · {data.bandit.formalism}
            </div>
            <div className="mt-2 grid gap-2 text-[12px] sm:grid-cols-2 xl:grid-cols-4">
              <div>
                <div className="font-semibold" style={{ color: colors.text.primary }}>State (context)</div>
                <div style={{ color: colors.text.muted }}>{data.bandit.state.source}</div>
              </div>
              <div>
                <div className="font-semibold" style={{ color: colors.text.primary }}>Action (arm)</div>
                <div style={{ color: colors.text.muted }}>{data.bandit.actions.arms}</div>
              </div>
              <div>
                <div className="font-semibold" style={{ color: colors.text.primary }}>Policy</div>
                <div className="font-mono text-[11px]" style={{ color: colors.text.muted }}>{data.bandit.policy.formula}</div>
              </div>
              <div>
                <div className="font-semibold" style={{ color: colors.text.primary }}>Update rule</div>
                <div className="font-mono text-[11px]" style={{ color: colors.text.muted }}>{data.bandit.update_rule.formula}</div>
              </div>
            </div>
            <p className="mt-2 text-[11px]" style={{ color: colors.text.muted }}>
              Reward clamp {data.bandit.reward.clamp} · neutral weight {data.bandit.update_rule.neutral_weight} ·{" "}
              {data.bandit.exploration}
            </p>
          </div>
        ) : null}

        {/* (a) What feedback does — the five real signals */}
        <div>
          <div className={type.label} style={{ color: colors.text.secondary }}>
            Step 1 · Every Feedback Action Is a Learning Signal
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {signals.map((s) => {
              const up = s.delta > 0;
              const fg = up ? colors.positive : colors.negative;
              return (
                <div
                  key={s.action}
                  className="flex items-center gap-1.5 rounded-lg border px-2 py-1"
                  style={{ borderColor: colors.surface.border, backgroundColor: colors.surface.canvas }}
                  title={s.summary}
                >
                  <span className={type.data} style={{ color: colors.text.primary, fontWeight: 600 }}>
                    {s.action.charAt(0) + s.action.slice(1).toLowerCase()}
                  </span>
                  <span className={type.data} style={{ color: fg, fontWeight: 600 }}>
                    {up ? "▲" : "▼"} {up ? "+" : ""}
                    {s.delta.toFixed(2)} weight
                  </span>
                  <span className={type.data} style={{ color: colors.text.muted }}>
                    reward {s.reward > 0 ? "+" : ""}
                    {s.reward.toFixed(1)}
                  </span>
                </div>
              );
            })}
          </div>
          <p className={`mt-1.5 ${type.data}`} style={{ color: colors.text.muted }}>
            Accepting or completing a recommendation pushes its action family&apos;s ranking weight up;
            rejecting or ignoring pushes it down. Weights stay between 0.50 and 1.50 (1.00 = neutral).
          </p>
        </div>

        {/* (b) Weights moving over feedback rounds — the centerpiece */}
        <div>
          <div className={type.label} style={{ color: colors.text.secondary }}>
            Step 2 · Ranking Weights Move With Every Round of Feedback
          </div>
          <div className="mt-2 h-[240px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
                <XAxis
                  dataKey="round"
                  tick={{ fontSize: 10, fill: colors.text.muted }}
                  tickLine={false}
                  axisLine={{ stroke: colors.surface.border }}
                  label={{ value: "feedback round", position: "insideBottom", offset: -2, fontSize: 10, fill: colors.text.muted }}
                />
                <YAxis
                  domain={[0.4, 1.6]}
                  ticks={[0.5, 0.75, 1.0, 1.25, 1.5]}
                  tick={{ fontSize: 10, fill: colors.text.muted }}
                  tickLine={false}
                  axisLine={false}
                  width={34}
                  tickFormatter={(v: number) => v.toFixed(2)}
                />
                <Tooltip
                  cursor={{ stroke: colors.text.muted, strokeDasharray: "3 3" }}
                  contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
                  labelFormatter={(r) => {
                    const row = chartData.find((d) => d.round === r);
                    return row
                      ? `Round ${r} — ${row.action.charAt(0) + row.action.slice(1).toLowerCase()} on ${familyLabel(row.action_family)}`
                      : `Round ${r}`;
                  }}
                  formatter={(value: number | string, name: string) => [
                    typeof value === "number" ? value.toFixed(2) : value,
                    familyLabel(String(name)),
                  ]}
                />
                <Legend
                  verticalAlign="top"
                  align="right"
                  iconType="plainline"
                  wrapperStyle={{ fontSize: 11, paddingBottom: 6 }}
                  formatter={(v: string) => familyLabel(v)}
                />
                <ReferenceLine
                  y={1.0}
                  stroke={colors.text.muted}
                  strokeDasharray="4 4"
                  label={{ value: "neutral (1.00)", position: "insideTopLeft", fontSize: 10, fill: colors.text.muted }}
                />
                {families.map((fam) => (
                  <Line
                    key={fam}
                    type="stepAfter"
                    dataKey={fam}
                    name={fam}
                    stroke={familyColor(families, fam)}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, strokeWidth: 0 }}
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className={`mt-1 ${type.data}`} style={{ color: colors.text.muted }}>
            Each line is one action family&apos;s ranking weight after every real feedback event.
            Lines diverging from the neutral 1.00 line are the system learning which action
            families this cohort finds valuable.
          </p>
        </div>

        {/* (c) Before -> after per family */}
        <div>
          <div className={type.label} style={{ color: colors.text.secondary }}>
            Step 3 · Where the Rankings Ended Up — and Why
          </div>
          <div className="mt-2 space-y-2">
            {data.baseline_vs_learned.map((row) => {
              const up = row.change > 0.005;
              const down = row.change < -0.005;
              const fg = up ? colors.positive : down ? colors.negative : colors.text.secondary;
              return (
                <div
                  key={row.family}
                  className="rounded-lg border px-3 py-2"
                  style={{ borderColor: colors.surface.border }}
                >
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="flex items-center gap-1.5">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-sm"
                        style={{ backgroundColor: familyColor(families, row.family) }}
                      />
                      <span className={type.body} style={{ color: colors.text.primary, fontWeight: 600 }}>
                        {familyLabel(row.family)}
                      </span>
                    </span>
                    <span className={type.data} style={{ color: colors.text.secondary }}>
                      {row.baseline_weight.toFixed(2)} {"→"}{" "}
                      <span style={{ color: fg, fontWeight: 700 }}>{row.learned_weight.toFixed(2)}</span>
                    </span>
                    <span className={type.data} style={{ color: fg, fontWeight: 600 }}>
                      {up ? "▲" : down ? "▼" : "▬"} {row.change >= 0 ? "+" : ""}
                      {row.change.toFixed(2)}
                    </span>
                    <span className={type.data} style={{ color: colors.text.muted }}>
                      {row.positive_events} positive / {row.negative_events} negative signals
                    </span>
                  </div>
                  <p className={`mt-1 ${type.data}`} style={{ color: colors.text.secondary }}>
                    {takeaway(row)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        <p className={type.data} style={{ color: colors.text.muted }}>
          {data.note}
        </p>
      </CardContent>
    </Card>
  );
}
