"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BadgeDollarSign, TrendingUp, CircleCheck, Target } from "lucide-react";

import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { apiClient } from "@/lib/api/client";
import { colors, type } from "@/styles/tokens";

interface LifecycleTotals { open: number; accepted: number; in_progress: number; completed: number; rejected: number; ignored: number; modified: number }
interface Totals {
  total_impact: number; completed_count: number; advisors_affected: number;
  by_family: Record<string, number>;
  by_advisor: Array<{ advisor_id: string; advisor_name: string; impact: number }>;
  lifecycle_totals?: LifecycleTotals;
}
interface Entry { impact_amount: number; created_ts: string }

const usd = (v: number) => `$${Math.round(v).toLocaleString()}`;
const pct = (n: number, d: number) => (d > 0 ? `${Math.round((n / d) * 100)}%` : "—");

export function BusinessImpactWorkspace() {
  const [totals, setTotals] = useState<Totals | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);

  useEffect(() => {
    apiClient.get<{ entries: Entry[]; totals: Totals }>("/impact-ledger")
      .then((r) => { setTotals(r.totals); setEntries(r.entries); })
      .catch(() => { setTotals(null); setEntries([]); });
  }, []);

  const lt = totals?.lifecycle_totals;
  const actioned = lt ? lt.accepted + lt.in_progress + lt.completed + lt.modified + lt.rejected + lt.ignored : 0;
  const acted = lt ? lt.accepted + lt.in_progress + lt.completed + lt.modified : 0;
  const inFlight = lt ? lt.accepted + lt.in_progress + lt.completed : 0;
  const acceptanceRate = pct(acted, actioned);
  const completionRate = pct(lt?.completed ?? 0, inFlight);

  // cumulative impact over time
  const byDate = new Map<string, number>();
  for (const e of [...entries].sort((a, b) => a.created_ts.localeCompare(b.created_ts))) {
    const d = (e.created_ts || "").slice(0, 10);
    byDate.set(d, (byDate.get(d) ?? 0) + e.impact_amount);
  }
  let run = 0;
  const cumulative = [...byDate.entries()].map(([date, v]) => { run += v; return { date, cumulative: run }; });
  const byFamily = Object.entries(totals?.by_family ?? {}).map(([family, impact]) => ({ family, impact }));
  const empty = (totals?.completed_count ?? 0) === 0;

  const OUTCOMES: Array<[string, string, string]> = [
    ["Increase Revenue", usd(totals?.total_impact ?? 0), "cumulative recorded impact"],
    ["Increase Advisor Productivity", completionRate, "recommendation completion rate"],
    ["Improve Goal Attainment", usd(totals?.by_family?.AGP_RESCUE ?? 0), "AGP-family recorded impact"],
    ["Increase NCF / AUM", "—", "impact_type supports NCF/AUM when a family records them"],
  ];

  return (
    <div className="space-y-3">
      <div>
        <div className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-semibold" style={{ borderColor: "#A7F3D0", background: "#F0FDF4", color: "#065F46" }}>
          <BadgeDollarSign className="h-3.5 w-3.5" /> Executive · Business Impact & ROI
        </div>
        <h2 className={`mt-2 ${type.pageTitle}`}>What the platform has driven</h2>
        <p className="max-w-3xl text-[12px] text-muted-foreground">
          The executive aggregate — cumulative dollar impact recorded from real completed recommendations,
          with acceptance and completion rates. (The <a href="/impact-ledger" className="font-semibold text-primary underline">Impact Ledger</a> is
          the per-entry audit trail; <a href="/recommendation-roi" className="font-semibold text-primary underline">Recommendation ROI</a> is the per-advisor learning analytics.)
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Cumulative Recorded Impact" value={usd(totals?.total_impact ?? 0)} icon={BadgeDollarSign} iconColor={colors.positive} />
        <KpiStatCard label="Recommendations Acted On" value={String(acted)} icon={CircleCheck} iconColor={colors.primary} />
        <KpiStatCard label="Acceptance Rate" value={acceptanceRate} icon={TrendingUp} iconColor="#4F46E5" />
        <KpiStatCard label="Completion Rate" value={completionRate} icon={Target} iconColor={colors.warning} />
      </div>

      {empty ? (
        <div className="rounded-xl border bg-white p-6 text-center text-[13px] text-muted-foreground shadow-sm" style={{ borderColor: colors.surface.border }}>
          No recommendations have been completed yet — cumulative impact appears here the moment one is.
          Run the <a href="/story" className="font-semibold text-primary underline">Guided Story Mode</a> to see the whole cycle, or complete one on{" "}
          <a href="/recommendations" className="font-semibold text-primary underline">Opportunities &amp; Recommendations</a>.
        </div>
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          <div className="rounded-xl border bg-white p-3 shadow-sm" style={{ borderColor: colors.surface.border }}>
            <div className="mb-1 text-[13px] font-semibold">Cumulative Recorded Impact Over Time</div>
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cumulative} margin={{ top: 8, right: 16, left: 4, bottom: 0 }}>
                  <defs><linearGradient id="biGrad" x1="0" x2="0" y1="0" y2="1"><stop offset="5%" stopColor={colors.positive} stopOpacity={0.35} /><stop offset="95%" stopColor={colors.positive} stopOpacity={0.02} /></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                  <YAxis tickFormatter={(v) => `$${Intl.NumberFormat("en-US", { notation: "compact" }).format(Number(v))}`} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} width={54} />
                  <Tooltip formatter={(v: number) => usd(Number(v))} />
                  <Area type="monotone" dataKey="cumulative" stroke={colors.positive} strokeWidth={2.5} fill="url(#biGrad)" isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="rounded-xl border bg-white p-3 shadow-sm" style={{ borderColor: colors.surface.border }}>
            <div className="mb-1 text-[13px] font-semibold">Impact by Action Family</div>
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byFamily} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.18} horizontal={false} />
                  <XAxis type="number" tickFormatter={(v) => `$${Intl.NumberFormat("en-US", { notation: "compact" }).format(Number(v))}`} tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="family" width={120} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => usd(Number(v))} />
                  <Bar dataKey="impact" radius={[0, 6, 6, 0]} isAnimationActive={false}>{byFamily.map((d) => <Cell key={d.family} fill={colors.primary} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Business-outcome mapping strip (poster language) */}
      <div className="rounded-xl border p-3" style={{ borderColor: "#C7D2FE", background: "#EEF2FF" }}>
        <div className={`mb-2 ${type.label}`} style={{ color: "#3730A3" }}>Business Outcomes (from the architecture posters)</div>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {OUTCOMES.map(([outcome, value, note]) => (
            <div key={outcome} className="rounded-lg border bg-white px-3 py-2" style={{ borderColor: "#C7D2FE" }}>
              <div className="text-[11px] font-bold" style={{ color: "#3730A3" }}>{outcome}</div>
              <div className="text-[18px] font-black" style={{ color: colors.text.primary }}>{value}</div>
              <div className="text-[10px]" style={{ color: colors.text.muted }}>{note}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
        <span className="font-semibold text-foreground">Evidence · </span>
        Cumulative impact = Σ real ledger transactions (phx_dm_local_impact_ledger); acceptance/completion
        rates from phx_dm_local_recommendation status counts. Acceptance = (accepted+in-progress+completed+
        modified) / all actioned; completion = completed / (accepted+in-progress+completed). NCF/AUM show
        &quot;—&quot; until a recommendation family records those impact types (the ledger&apos;s impact_type column supports them).
      </div>
    </div>
  );
}
