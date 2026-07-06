"use client";
import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingUp, Brain, Trophy, DollarSign, ThumbsUp, Activity } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import { fetchImpactTrend, generateRecommendations, type ImpactTrend, type Recommendation } from "@/lib/api/roi";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { colors } from "@/styles/tokens";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

const SEV_VARIANT: Record<string, "success" | "warning" | "destructive" | "glass"> = {
  Critical: "destructive", Urgent: "warning", Attention: "warning", Info: "glass",
};

export function RecommendationROIWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [trend, setTrend] = useState<ImpactTrend | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);

  useEffect(() => {
    apiClient
      .get<{ advisors: Array<{ advisor_id: string; advisor_name: string | null }> }>("/advisor/list")
      .then((r) => setAdvisors(r.advisors))
      .catch(() => setAdvisors([]));
  }, []);

  useEffect(() => {
    if (shell.scopeType === "Advisor") setAdvisorId(shell.scopeId);
    else resolveScope(shell.scopeType, shell.scopeId).then((r) => setAdvisorId(r.advisor_ids[0] ?? "A001")).catch(() => undefined);
  }, [shell.scopeType, shell.scopeId]);

  const load = useCallback(async () => {
    // Scope the feedback-learning replay to the SELECTED advisor so the top cards,
    // reward curve and weights reflect that advisor (was a firm-wide static cohort).
    const [t, r] = await Promise.all([fetchImpactTrend(advisorId), generateRecommendations(advisorId)]);
    setTrend(t);
    setRecs(r);
  }, [advisorId, shell.refreshNonce]);

  useEffect(() => {
    void load();
  }, [load]);

  const totals = trend?.totals;
  const acceptRate =
    totals && totals.accepted + totals.rejected > 0
      ? Math.round((totals.accepted / (totals.accepted + totals.rejected)) * 100)
      : 0;
  const advisorName = advisors.find((a) => a.advisor_id === advisorId)?.advisor_name ?? advisorId;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Recommendation Impact / ROI</Badge>
          <h2 className="mt-2 text-[22px] font-black">{advisorName} · Outcome &amp; Learning Loop</h2>
          <p className="text-[12px] text-muted-foreground">
            Real feedback-learning signals for <strong>{advisorName}</strong>: accept/reject/complete events move
            per-family learning weights, which re-rank future recommendations — scoped to the selected advisor.
          </p>
        </div>
        <select
          className="h-8 rounded-lg border border-border bg-background px-2 text-[12px]"
          value={advisorId}
          onChange={(e) => setAdvisorId(e.target.value)}
        >
          {advisors.length === 0 && <option value={advisorId}>{advisorId}</option>}
          {advisors.map((a) => (
            <option key={a.advisor_id} value={a.advisor_id}>{a.advisor_name ?? a.advisor_id}</option>
          ))}
        </select>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Captured Impact" value={totals ? compactUsd(totals.captured_impact) : "—"} icon={DollarSign} iconColor={colors.positive} />
        <KpiStatCard label="Accept Rate" value={`${acceptRate}%`} delta={totals ? `${totals.accepted}/${totals.accepted + totals.rejected}` : undefined} deltaPositive icon={ThumbsUp} iconColor={colors.primary} />
        <KpiStatCard label="Feedback Events" value={String(trend?.event_count ?? "—")} icon={Activity} iconColor={colors.aiAccent} />
        <KpiStatCard label="Cumulative Reward" value={totals ? totals.cumulative_reward.toFixed(1) : "—"} icon={Brain} iconColor={colors.warning} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <TrendingUp className="h-4 w-4 text-primary" /> Cumulative Reward Curve (RL signal)
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3">
            <div className="h-[240px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend?.trend ?? []} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
                  <defs>
                    <linearGradient id="rewardGrad" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="5%" stopColor={colors.aiAccent} stopOpacity={0.32} />
                      <stop offset="95%" stopColor={colors.aiAccent} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
                  <XAxis dataKey="round" tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={{ stroke: colors.surface.border }} />
                  <YAxis tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={false} width={32} />
                  <ReferenceLine y={0} stroke={colors.surface.border} />
                  <Tooltip
                    contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
                    formatter={(v: number) => [v.toFixed(2), "Cumulative reward"]}
                    labelFormatter={(l, p) => {
                      const pt = p?.[0]?.payload;
                      return pt ? `Round ${l} · ${pt.action} · ${pt.action_family}` : `Round ${l}`;
                    }}
                  />
                  <Area isAnimationActive={false} type="monotone" dataKey="cumulative_reward" stroke={colors.aiAccent} strokeWidth={2.5} fill="url(#rewardGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Brain className="h-4 w-4 text-primary" /> Learned Family Weights
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3">
            <div className="h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trend?.final_weights ?? []} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 8 }}>
                  <CartesianGrid horizontal={false} stroke={colors.surface.border} strokeOpacity={0.6} />
                  <XAxis type="number" domain={[0, 2]} tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={{ stroke: colors.surface.border }} />
                  <YAxis type="category" dataKey="family" tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={false} width={104} tickFormatter={(s: string) => s.replace("_", " ")} />
                  <ReferenceLine x={1} stroke={colors.text.muted} strokeDasharray="3 3" label={{ value: "baseline", fontSize: 9, fill: colors.text.muted }} />
                  <Tooltip contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }} formatter={(v: number, _n, p) => [`weight ${v} · ${(p.payload as { events: number }).events} events`, "Learned"]} />
                  <Bar isAnimationActive={false} dataKey="weight" radius={[0, 6, 6, 0]} barSize={22}>
                    {(trend?.final_weights ?? []).map((w) => (
                      <Cell key={w.family} fill={w.weight >= 1 ? colors.positive : colors.warning} />
                    ))}
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
            <Trophy className="h-4 w-4 text-primary" /> {advisorName} · Recommendations Re-Ranked by Learning
          </CardTitle>
          <span className="text-[10px] text-muted-foreground">priority = base × learning weight</span>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                  <th className="px-3 py-2">Recommendation</th>
                  <th className="px-3 py-2">Family</th>
                  <th className="px-3 py-2 text-right">Base</th>
                  <th className="px-3 py-2 text-right">×Weight</th>
                  <th className="px-3 py-2 text-right">Priority</th>
                  <th className="px-3 py-2 text-right">Impact</th>
                  <th className="px-3 py-2">Severity</th>
                </tr>
              </thead>
              <tbody>
                {recs.map((r) => (
                  <tr key={r.recommendation_id} className="border-b last:border-0">
                    <td className="px-3 py-2">
                      <div className="font-medium">{r.title}</div>
                      <div className="text-[11px] text-muted-foreground">conf {(r.confidence * 100).toFixed(0)}%</div>
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">{r.action_family.replace("_", " ")}</td>
                    <td className="px-3 py-2 text-right font-mono">{r.base_priority_score.toFixed(1)}</td>
                    <td className="px-3 py-2 text-right font-mono" style={{ color: r.learning_weight >= 1 ? colors.positive : colors.warning }}>
                      ×{r.learning_weight.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono font-bold">{r.priority_score.toFixed(1)}</td>
                    <td className="px-3 py-2 text-right font-mono">{compactUsd(r.estimated_revenue_impact)}</td>
                    <td className="px-3 py-2"><Badge variant={SEV_VARIANT[r.severity] ?? "glass"}>{r.severity}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {trend?.note && (
        <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Evidence · </span>{trend.note}
        </div>
      )}
    </div>
  );
}
