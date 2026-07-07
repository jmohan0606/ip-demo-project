"use client";
import { useCallback, useEffect, useState } from "react";
import { Filter, Users, Phone, ClipboardList, CalendarDays, Mail, StickyNote, CheckSquare } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import {
  fetchCrmPipeline,
  fetchCrmOpportunities,
  fetchCrmLeads,
  fetchCrmReferrals,
  fetchCrmActivities,
  type CrmPipelineStage,
  type CrmOpportunity,
  type CrmWorkItem,
  type CrmActivitiesData,
} from "@/lib/api/crm";
import { CrmStageFunnel } from "@/components/charts/crm-stage-funnel";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { colors, type } from "@/styles/tokens";

const ACTIVITY_ICON: Record<string, LucideIcon> = {
  MEETING: Users, CALL: Phone, EMAIL: Mail, REVIEW: CalendarDays, FOLLOW_UP: CheckSquare,
};
const SENTIMENT_COLOR: Record<string, string> = { POSITIVE: colors.positive, NEUTRAL: colors.text.muted, NEGATIVE: colors.negative };

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
  const [activity, setActivity] = useState<CrmActivitiesData | null>(null);

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
    const [p, o, l, r, act] = await Promise.all([
      fetchCrmPipeline(advisorId),
      fetchCrmOpportunities(advisorId),
      fetchCrmLeads(advisorId),
      fetchCrmReferrals(advisorId),
      fetchCrmActivities(advisorId),
    ]);
    setPipeline(p);
    setOpps(o);
    setLeads(l);
    setReferrals(r);
    setActivity(act);
  }, [advisorId, shell.refreshNonce]);

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
          <h2 className={`mt-2 ${type.pageTitle}`}>{advisorName} · Pipeline &amp; Activity</h2>
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
              <CrmStageFunnel data={pipeline} />
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

      {/* Activities This Week — icon-labelled counts by type (CLAUDE.md 9.12) */}
      <Card>
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]"><CalendarDays className="h-4 w-4 text-primary" /> Activities This Week</CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {["MEETING", "CALL", "EMAIL", "REVIEW", "FOLLOW_UP"].map((t) => {
              const Icon = ACTIVITY_ICON[t] ?? ClipboardList;
              const week = activity?.this_week[t] ?? 0;
              const total = activity?.by_type[t] ?? 0;
              return (
                <div key={t} className="flex items-center gap-2.5 rounded-xl border p-3" style={{ borderColor: colors.surface.border }}>
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full" style={{ backgroundColor: `${colors.primary}14`, color: colors.primary }}>
                    <Icon style={{ width: 18, height: 18 }} />
                  </span>
                  <div>
                    <div className="text-[18px] font-black" style={{ color: colors.text.primary }}>{week}</div>
                    <div className="text-[10px] uppercase tracking-[0.05em]" style={{ color: colors.text.muted }}>{t.replace("_", " ")} · {total} total</div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Recent Meetings — exact columns: Date, Subject, With, Type, Outcome, Next Step (9.12) */}
      <Card>
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]"><Users className="h-4 w-4 text-primary" /> Recent Meetings</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Subject</th>
                  <th className="px-3 py-2">With</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Outcome</th>
                  <th className="px-3 py-2">Next Step</th>
                </tr>
              </thead>
              <tbody>
                {(activity?.recent_meetings ?? []).map((m) => (
                  <tr key={m.activity_id} className="border-b last:border-0">
                    <td className="px-3 py-2 font-mono text-[11px]">{m.activity_date}</td>
                    <td className="px-3 py-2 font-medium" style={{ color: colors.text.primary }}>{m.subject}</td>
                    <td className="px-3 py-2 text-muted-foreground">{m.with}</td>
                    <td className="px-3 py-2"><Badge variant="glass">{m.activity_type?.replace("_", " ")}</Badge></td>
                    <td className="px-3 py-2">
                      <span className="font-semibold" style={{ color: SENTIMENT_COLOR[m.sentiment?.toUpperCase() ?? ""] ?? colors.text.muted }}>{m.status}</span>
                      {m.sentiment && <span className="ml-1 text-[10px]" style={{ color: SENTIMENT_COLOR[m.sentiment.toUpperCase()] ?? colors.text.muted }}>· {m.sentiment.toLowerCase()}</span>}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">{m.next_action}{m.next_action_date ? ` (${m.next_action_date})` : ""}</td>
                  </tr>
                ))}
                {(activity?.recent_meetings ?? []).length === 0 && (
                  <tr><td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">No meetings recorded.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 xl:grid-cols-2">
        <WorkTable title="Leads" icon={<ClipboardList className="h-4 w-4 text-primary" />} items={leads} />
        <WorkTable title="Referrals" icon={<Phone className="h-4 w-4 text-primary" />} items={referrals} />
      </div>

      {/* Recent Notes — vary per advisor (9.12) */}
      <Card>
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]"><StickyNote className="h-4 w-4 text-primary" /> Recent Notes</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 p-3 md:grid-cols-2">
          {(activity?.activities ?? []).filter((a) => a.notes_summary).slice(0, 6).map((a) => {
            const Icon = ACTIVITY_ICON[a.activity_type ?? ""] ?? ClipboardList;
            return (
              <div key={a.activity_id} className="rounded-xl border p-3" style={{ borderColor: colors.surface.border }}>
                <div className="flex items-center gap-2">
                  <Icon className="h-3.5 w-3.5" style={{ color: colors.primary }} />
                  <span className="text-[12px] font-semibold" style={{ color: colors.text.primary }}>{a.subject}</span>
                  <span className="ml-auto font-mono text-[10px]" style={{ color: colors.text.muted }}>{a.activity_date}</span>
                </div>
                <p className="mt-1 text-[11px]" style={{ color: colors.text.secondary }}>{a.notes_summary}</p>
              </div>
            );
          })}
        </CardContent>
      </Card>
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
