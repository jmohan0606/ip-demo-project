"use client";
import { useCallback, useEffect, useState } from "react";
import { Building2, TrendingUp, Users, Target } from "lucide-react";
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
  }, [load]);

  const t = data?.totals;
  const childHeading = CHILD_LABEL[shell.scopeType] ?? "Breakdown";
  const isAdvisor = shell.scopeType === "Advisor";

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
        <KpiStatCard label="Advisors In Scope" value={String(t?.advisor_count ?? "—")} />
        <KpiStatCard label="Revenue (LTM)" value={t ? compactUsd(t.revenue_ltm) : "—"} />
        <KpiStatCard label="AUM" value={t ? compactUsd(t.aum_total) : "—"} />
        <KpiStatCard label="NNM (Annualized)" value={t ? compactUsd(t.nnm_annualized) : "—"} />
        <KpiStatCard label="Managed Revenue" value={t ? compactUsd(t.managed_revenue) : "—"} />
        <KpiStatCard
          label="Avg Goal Attainment"
          value={t ? `${t.avg_goal_attainment}%` : "—"}
        />
        <KpiStatCard label="Avg AGP Risk Score" value={t ? String(t.avg_agp_risk_score) : "—"} />
        <KpiStatCard
          label="At-Risk Advisors"
          value={
            t
              ? String(t.status_distribution.attention + t.status_distribution.urgent + t.status_distribution.critical)
              : "—"
          }
        />
      </div>

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

      <Card>
        <CardHeader className="flex flex-row items-center justify-between p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <TrendingUp className="h-4 w-4 text-primary" /> Top Advisors In Scope
          </CardTitle>
          <Users className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                  <th className="px-3 py-2">Advisor</th>
                  <th className="px-3 py-2 text-right">Revenue (LTM)</th>
                  <th className="px-3 py-2 text-right">AUM</th>
                  <th className="px-3 py-2 text-right">Goal</th>
                  <th className="px-3 py-2 text-right">Risk</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {(data?.top_advisors ?? []).map((a) => (
                  <tr
                    key={a.advisor_id}
                    className="cursor-pointer border-b last:border-0 hover:bg-muted/40"
                    onClick={() => shell.setScope("Advisor", a.advisor_id, a.advisor_name)}
                  >
                    <td className="px-3 py-2 font-medium">{a.advisor_name}</td>
                    <td className="px-3 py-2 text-right font-mono">{compactUsd(a.revenue_ltm)}</td>
                    <td className="px-3 py-2 text-right font-mono">{compactUsd(a.aum_total)}</td>
                    <td className="px-3 py-2 text-right font-mono">{a.goal_attainment}%</td>
                    <td className="px-3 py-2 text-right font-mono">{a.agp_risk_score}</td>
                    <td className="px-3 py-2">
                      <Badge variant={STATUS_STYLE[a.status] ?? "glass"}>{a.status.replace("_", " ")}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

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
