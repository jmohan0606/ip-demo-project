"use client";
import { useCallback, useEffect, useState } from "react";
import { Filter, Users, Phone, ClipboardList } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import {
  fetchCrmPipeline,
  fetchCrmOpportunities,
  fetchCrmLeads,
  fetchCrmReferrals,
  type CrmPipelineStage,
  type CrmOpportunity,
  type CrmWorkItem,
} from "@/lib/api/crm";
import { CrmPipelineFunnel } from "@/components/charts/crm-pipeline-funnel";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "glass"> = {
  WON: "success", CONVERTED: "success", COMPLETED: "success", CLOSED_WON: "success",
  OVERDUE: "destructive", LOST: "destructive", CLOSED_LOST: "destructive",
  PENDING: "warning", OPEN: "warning", NEGOTIATE: "warning",
};

const variant = (s: string) => STATUS_VARIANT[s?.toUpperCase()] ?? "glass";

export function CrmActivitiesWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [pipeline, setPipeline] = useState<CrmPipelineStage[]>([]);
  const [opps, setOpps] = useState<CrmOpportunity[]>([]);
  const [leads, setLeads] = useState<CrmWorkItem[]>([]);
  const [referrals, setReferrals] = useState<CrmWorkItem[]>([]);

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
    const [p, o, l, r] = await Promise.all([
      fetchCrmPipeline(advisorId),
      fetchCrmOpportunities(advisorId),
      fetchCrmLeads(advisorId),
      fetchCrmReferrals(advisorId),
    ]);
    setPipeline(p);
    setOpps(o);
    setLeads(l);
    setReferrals(r);
  }, [advisorId]);

  useEffect(() => {
    void load();
  }, [load]);

  const advisorName = advisors.find((a) => a.advisor_id === advisorId)?.advisor_name ?? advisorId;
  const totalPipeline = pipeline.reduce((s, p) => s + p.pipeline_amount, 0);
  const weighted = pipeline.reduce((s, p) => s + p.weighted_amount, 0);
  const overdue = [...leads, ...referrals].filter((i) => i.overdue).length;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">CRM Activities</Badge>
          <h2 className="mt-2 text-[22px] font-black">{advisorName} · Pipeline &amp; Activity</h2>
          <p className="text-[12px] text-muted-foreground">
            Real leads, referrals and opportunities with pipeline stages, weighted value and overdue
            work — the same records that feed the CRM feature inputs.
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
        <KpiStatCard label="Total Pipeline" value={compactUsd(totalPipeline)} />
        <KpiStatCard label="Weighted Pipeline" value={compactUsd(weighted)} />
        <KpiStatCard label="Open Opportunities" value={String(opps.length)} />
        <KpiStatCard label="Overdue Items" value={String(overdue)} delta={overdue > 0 ? "action" : "clear"} deltaPositive={overdue === 0} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Filter className="h-4 w-4 text-primary" /> Pipeline by Stage
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3">
            {pipeline.length > 0 ? (
              <CrmPipelineFunnel data={pipeline} />
            ) : (
              <div className="p-8 text-center text-[12px] text-muted-foreground">No open pipeline.</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Users className="h-4 w-4 text-primary" /> Opportunities ({opps.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="max-h-[260px] overflow-auto">
              <table className="w-full text-[12px]">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2">Opportunity</th>
                    <th className="px-3 py-2">Stage</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                    <th className="px-3 py-2 text-right">Close</th>
                  </tr>
                </thead>
                <tbody>
                  {opps.map((o) => (
                    <tr key={o.id} className="border-b last:border-0">
                      <td className="px-3 py-2">{o.name}</td>
                      <td className="px-3 py-2"><Badge variant={variant(o.stage)}>{o.stage.replace("_", " ")}</Badge></td>
                      <td className="px-3 py-2 text-right font-mono">{compactUsd(o.amount)}</td>
                      <td className="px-3 py-2 text-right text-muted-foreground">{o.expected_close_date ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <WorkTable title="Leads" icon={<ClipboardList className="h-4 w-4 text-primary" />} items={leads} />
        <WorkTable title="Referrals" icon={<Phone className="h-4 w-4 text-primary" />} items={referrals} />
      </div>
    </div>
  );
}

function WorkTable({ title, icon, items }: { title: string; icon: React.ReactNode; items: CrmWorkItem[] }) {
  const compactUsd = (v: number) => `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;
  return (
    <Card>
      <CardHeader className="p-3">
        <CardTitle className="flex items-center gap-2 text-[13px]">{icon} {title} ({items.length})</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="max-h-[240px] overflow-auto">
          <table className="w-full text-[12px]">
            <thead className="sticky top-0 bg-card">
              <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Est. Value</th>
                <th className="px-3 py-2 text-right">Age</th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.id} className={`border-b last:border-0 ${i.overdue ? "bg-red-50/40" : ""}`}>
                  <td className="px-3 py-2 font-mono text-[11px]">{i.id}</td>
                  <td className="px-3 py-2 text-muted-foreground">{i.source}</td>
                  <td className="px-3 py-2">
                    <Badge variant={STATUS_VARIANT[i.status?.toUpperCase()] ?? "glass"}>{i.status}</Badge>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{compactUsd(i.estimated_value)}</td>
                  <td className="px-3 py-2 text-right text-muted-foreground">{i.age_days ?? "—"}d</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
