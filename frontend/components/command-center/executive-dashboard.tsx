"use client";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Building2, TrendingUp, TrendingDown, Users, Target, DollarSign, Wallet, PiggyBank, Layers, Gauge, ShieldAlert, AlertTriangle } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { fetchScopeSummary, type ScopeSummary } from "@/lib/api/scope";
import { ScopeChildBars } from "@/components/charts/scope-child-bars";
import { ScopeStatusDonut } from "@/components/charts/scope-status-donut";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ScopeType } from "@/lib/types/navigation";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

const CHILD_LABEL: Record<string, string> = {
  Firm: "Divisions",
  Division: "Regions",
  Region: "Markets",
  Market: "Advisors",
};

const STATUS_STYLE: Record<string, "success" | "warning" | "destructive"> = {
  on_track: "success",
  attention: "warning",
  urgent: "warning",
  critical: "destructive",
};

function AdvisorTable({
  title,
  icon,
  rows,
  onSelect,
}: {
  title: string;
  icon: ReactNode;
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
                <th className="px-3 py-2 text-right">Risk</th>
                <th className="px-3 py-2">Why</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.advisor_id} className="cursor-pointer border-b last:border-0 hover:bg-muted/40" onClick={() => onSelect("Advisor", a.advisor_id, a.advisor_name)}>
                  <td className="px-3 py-2 font-medium">{a.advisor_name}</td>
                  <td className="px-3 py-2 text-right font-mono">{compactUsd(a.revenue_ltm)}</td>
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

export function ExecutiveDashboard() {
  const shell = useShellContext();
  const [data, setData] = useState<ScopeSummary | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setData(await fetchScopeSummary(shell.scopeType.toUpperCase(), shell.scopeId));
    } finally {
      setBusy(false);
    }
  }, [shell.scopeType, shell.scopeId]);

  useEffect(() => {
    void load();
  }, [load, shell.refreshNonce]);

  const t = data?.totals;
  const cmp = data?.comparison;
  const revDelta = cmp?.revenue_change_pct;
  const childHeading = CHILD_LABEL[shell.scopeType] ?? "Breakdown";
  const isAdvisor = shell.scopeType === "Advisor";
  const atRisk = t ? t.status_distribution.attention + t.status_distribution.urgent + t.status_distribution.critical : 0;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Command Center</Badge>
          <h2 className="mt-2 text-[22px] font-black">{shell.scopeLabel || shell.scopeId} Overview</h2>
          <p className="text-[12px] text-muted-foreground">
            {shell.scopeType} scope · {t?.advisor_count ?? "—"} advisors — every figure aggregated from
            real per-advisor feature snapshots. Change scope in the breadcrumb to re-roll the whole page.
          </p>
        </div>
        {busy && <span className="text-[12px] text-muted-foreground">Rolling up…</span>}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Advisors In Scope" value={String(t?.advisor_count ?? "—")} icon={Users} iconColor="#2563EB" />
        <KpiStatCard label="Revenue (LTM)" value={t ? compactUsd(t.revenue_ltm) : "—"} icon={DollarSign} iconColor="#2563EB" changePct={revDelta} deltaSuffix="vs prior yr" />
        <KpiStatCard label="AUM" value={t ? compactUsd(t.aum_total) : "—"} icon={Wallet} iconColor="#14B8A6" />
        <KpiStatCard label="NNM (Annualized)" value={t ? compactUsd(t.nnm_annualized) : "—"} icon={PiggyBank} iconColor="#14B8A6" />
        <KpiStatCard label="Managed Revenue" value={t ? compactUsd(t.managed_revenue) : "—"} icon={Layers} iconColor="#4F46E5" />
        <KpiStatCard label="Avg Goal Attainment" value={t ? `${t.avg_goal_attainment}%` : "—"} icon={Gauge} iconColor="#4F46E5" />
        <KpiStatCard label="Avg AGP Risk Score" value={t ? String(t.avg_agp_risk_score) : "—"} icon={ShieldAlert} iconColor="#F59E0B" />
        <KpiStatCard label="At-Risk Advisors" value={t ? String(atRisk) : "—"} icon={AlertTriangle} iconColor="#DC2626" />
      </div>

      {/* Section 11.11 — business-outcome mapping (poster "Business Outcomes") */}
      <div className="flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2 text-[11px]" style={{ borderColor: "#C7D2FE", background: "#EEF2FF", color: "#3730A3" }}>
        <span className="font-semibold uppercase tracking-wide">Business Outcomes:</span>
        {[["Revenue (LTM)", "Increase Revenue"], ["AUM", "Increase AUM"], ["NNM", "Increase NCF"],
          ["Goal Attainment", "Improve Goal Attainment"], ["At-Risk / Coaching", "Increase Advisor Productivity"]].map(([kpi, outcome]) => (
          <span key={kpi} className="rounded-full border bg-white px-2 py-0.5" style={{ borderColor: "#C7D2FE" }}>{kpi} → <b>{outcome}</b></span>
        ))}
      </div>

      {/* AGP Program Status (9.5) */}
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

      {!isAdvisor && (
        <div className="grid gap-3 xl:grid-cols-[1.5fr_1fr]">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between p-3">
              <CardTitle className="flex items-center gap-2 text-[13px]">
                <Building2 className="h-4 w-4 text-primary" /> Revenue by {childHeading}
              </CardTitle>
              <span className="text-[10px] text-muted-foreground">click a bar to drill in</span>
            </CardHeader>
            <CardContent className="p-3">
              {data && data.child_breakdown.length > 0 ? (
                <ScopeChildBars
                  data={data.child_breakdown}
                  onSelect={(c) => shell.setScope(c.scope_type as ScopeType, c.scope_id, c.label)}
                />
              ) : (
                <div className="p-8 text-center text-[12px] text-muted-foreground">No sub-scopes.</div>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="p-3">
              <CardTitle className="flex items-center gap-2 text-[13px]">
                <Target className="h-4 w-4 text-primary" /> Advisor Status Mix
              </CardTitle>
            </CardHeader>
            <CardContent className="p-3">
              {t && <ScopeStatusDonut data={t.status_distribution} />}
            </CardContent>
          </Card>
        </div>
      )}

      {!isAdvisor && (
        <div className="grid gap-3 xl:grid-cols-2">
          <AdvisorTable title="Top Advisors" icon={<TrendingUp className="h-4 w-4 text-teal-600" />} rows={data?.top_advisors ?? []} onSelect={shell.setScope} />
          <AdvisorTable title="Needs Attention" icon={<TrendingDown className="h-4 w-4 text-red-600" />} rows={data?.bottom_advisors ?? []} onSelect={shell.setScope} />
        </div>
      )}

      {data && (
        <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Evidence · </span>
          {data.evidence.source}. {data.evidence.advisor_ids_resolved} advisors resolved under{" "}
          {data.scope_type} {data.scope_id} (sample {data.evidence.advisor_ids_sample.slice(0, 5).join(", ")}). ƒ{" "}
          {data.evidence.computation}
        </div>
      )}
    </div>
  );
}
