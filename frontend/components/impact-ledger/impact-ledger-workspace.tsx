"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Receipt, DollarSign, CircleCheck, Users, Clock, ChevronDown, ChevronRight, ExternalLink } from "lucide-react";

import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { AdvisorSelector } from "@/components/status/advisor-selector";
import { useShellContext } from "@/components/layout/shell-context";
import { fetchImpactLedger, fetchRecLifecycle, type LedgerResponse, type RecLifecycle } from "@/lib/api/impact-ledger";
import { colors } from "@/styles/tokens";

const usd = (v: number) => `$${Math.round(v).toLocaleString()}`;

export function ImpactLedgerWorkspace() {
  const shell = useShellContext();
  const [data, setData] = useState<LedgerResponse | null>(null);
  const [scope, setScope] = useState<"ALL" | string>("ALL");
  const [open, setOpen] = useState<string | null>(null);
  const [lifecycle, setLifecycle] = useState<Record<string, RecLifecycle>>({});

  const load = useCallback(async () => {
    setData(await fetchImpactLedger(scope));
  }, [scope]);

  useEffect(() => { void load(); }, [load, shell.refreshNonce]);

  const toggle = async (recId: string) => {
    if (open === recId) { setOpen(null); return; }
    setOpen(recId);
    if (!lifecycle[recId]) {
      try {
        const lc = await fetchRecLifecycle(recId);
        setLifecycle((p) => ({ ...p, [recId]: lc }));
      } catch { /* keep row */ }
    }
  };

  const t = data?.totals;
  const entries = data?.entries ?? [];
  // bucket impact by date for the trend bar
  const byDate = new Map<string, number>();
  for (const e of entries) {
    const d = (e.created_ts || "").slice(0, 10);
    byDate.set(d, (byDate.get(d) ?? 0) + e.impact_amount);
  }
  const trend = [...byDate.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, impact]) => ({ date, impact }));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-semibold" style={{ borderColor: "#A7F3D0", background: "#F0FDF4", color: "#065F46" }}>
            <Receipt className="h-3.5 w-3.5" /> iPerform Insights and Coaching · Impact Ledger
          </div>
          <h2 className="mt-2 text-[22px] font-black">Recommendation Impact Ledger</h2>
          <p className="text-[12px] text-muted-foreground">
            Every completed recommendation records a real, persisted consequence — a transaction generated from the
            recommendation&apos;s own estimated impact, linked back to the rec and its evidence chain. This is the live
            record that the Advisor 360, Revenue and Executive rollups reflect.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <AdvisorSelector />
          <button onClick={() => setScope("ALL")} className={`h-8 rounded-lg border px-2.5 text-[12px] font-semibold ${scope === "ALL" ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground"}`}>All advisors</button>
          <button onClick={() => setScope(shell.scopeType === "Advisor" ? shell.scopeId : "ALL")} disabled={shell.scopeType !== "Advisor"} className={`h-8 rounded-lg border px-2.5 text-[12px] font-semibold disabled:opacity-40 ${scope !== "ALL" ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground"}`}>Selected advisor</button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Total Recorded Impact" value={t ? usd(t.total_impact) : "—"} icon={DollarSign} iconColor={colors.positive} />
        <KpiStatCard label="Completed Recommendations" value={String(t?.completed_count ?? 0)} icon={CircleCheck} iconColor="#059669" />
        <KpiStatCard label="Advisors Affected" value={String(t?.advisors_affected ?? 0)} icon={Users} iconColor={colors.primary} />
        <KpiStatCard label="Latest Completion" value={t?.latest ? (t.latest.created_ts || "").slice(0, 10) : "—"} icon={Clock} iconColor={colors.warning} />
      </div>

      {trend.length >= 2 ? (
        <div className="rounded-xl border bg-white p-3 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <div className="mb-1 text-[13px] font-semibold">Recorded Impact Over Time</div>
          <div className="h-[200px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trend} margin={{ top: 8, right: 16, left: 4, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tickFormatter={(v) => `$${Intl.NumberFormat("en-US", { notation: "compact" }).format(Number(v))}`} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} width={54} />
                <Tooltip formatter={(v: number) => usd(Number(v))} />
                <Bar dataKey="impact" radius={[6, 6, 0, 0]} isAnimationActive={false}>
                  {trend.map((d) => <Cell key={d.date} fill={colors.positive} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : entries.length === 0 ? (
        <div className="rounded-xl border bg-white p-6 text-center text-[13px] text-muted-foreground shadow-sm" style={{ borderColor: colors.surface.border }}>
          No impact recorded yet. Complete a recommendation on the{" "}
          <a href="/recommendations" className="font-semibold text-primary underline">Opportunities &amp; Recommendations</a>{" "}
          page — its estimated impact becomes a real transaction here.
        </div>
      ) : null}

      <div className="rounded-xl border bg-white shadow-sm" style={{ borderColor: colors.surface.border }}>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                <th className="px-3 py-2" />
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Advisor</th>
                <th className="px-3 py-2">Recommendation</th>
                <th className="px-3 py-2">Family</th>
                <th className="px-3 py-2 text-right">Impact</th>
                <th className="px-3 py-2">Transaction</th>
                <th className="px-3 py-2">Note</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <Fragment key={e.ledger_id}>
                  <tr className="cursor-pointer border-b hover:bg-muted/40" onClick={() => toggle(e.recommendation_id)}>
                    <td className="px-3 py-2 text-muted-foreground">{open === e.recommendation_id ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}</td>
                    <td className="px-3 py-2 font-mono">{(e.created_ts || "").slice(0, 10)}</td>
                    <td className="px-3 py-2 font-medium">{e.advisor_name}</td>
                    <td className="px-3 py-2">{e.recommendation_title}</td>
                    <td className="px-3 py-2"><span className="rounded-full border px-2 py-0.5 text-[11px] font-semibold" style={{ color: colors.primary, background: "#EFF6FF", borderColor: "#BFDBFE" }}>{e.action_family ?? "—"}</span></td>
                    <td className="px-3 py-2 text-right font-mono font-semibold" style={{ color: colors.positive }}>+{usd(e.impact_amount)}</td>
                    <td className="px-3 py-2"><span className="font-mono text-[11px] text-muted-foreground">{e.source_transaction_id}</span></td>
                    <td className="px-3 py-2 text-[11px] text-muted-foreground">{e.note}</td>
                  </tr>
                  {open === e.recommendation_id && (
                    <tr className="border-b bg-slate-50/60">
                      <td colSpan={8} className="px-4 py-3">
                        {lifecycle[e.recommendation_id] ? (
                          <div className="space-y-2">
                            <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Lifecycle Timeline</div>
                            <div className="flex flex-wrap items-center gap-1.5">
                              {lifecycle[e.recommendation_id].transitions.map((tr, i) => (
                                <span key={i} className="inline-flex items-center gap-1">
                                  {i > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                                  <span className="rounded-md border px-2 py-0.5 text-[11px]" style={{ borderColor: colors.surface.border }} title={`${tr.actor_type} ${tr.actor_id ?? ""} · ${(tr.created_ts || "").slice(0, 19)}`}>
                                    {tr.to_status}
                                  </span>
                                </span>
                              ))}
                            </div>
                            <div className="flex flex-wrap gap-4 text-[11px] text-muted-foreground">
                              <span>Recommendation <span className="font-mono text-foreground">{e.recommendation_id}</span></span>
                              {e.opportunity_id && <span>Opportunity <span className="font-mono text-foreground">{e.opportunity_id}</span></span>
                              }
                              <a href="/memory-explainability" className="inline-flex items-center gap-1 font-semibold text-primary">Evidence chain ({lifecycle[e.recommendation_id].reasoning_trace_id}) <ExternalLink className="h-3 w-3" /></a>
                            </div>
                          </div>
                        ) : <div className="text-[12px] text-muted-foreground">Loading lifecycle…</div>}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {entries.length === 0 && (
                <tr><td colSpan={8} className="px-3 py-4 text-center text-muted-foreground">No ledger entries.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
        <span className="font-semibold text-foreground">Evidence · </span>
        Source: phx_dm_local_impact_ledger (SQLite) · injected phx_dm_revenue_transaction vertices via
        phx_dm_transaction_from_recommendation edges · impact amount = the recommendation&apos;s own
        estimated_revenue_impact (not an arbitrary figure).
      </div>
    </div>
  );
}
