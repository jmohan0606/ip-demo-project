"use client";
import { useCallback, useEffect, useState } from "react";
import { Target, Gauge, CalendarClock, Users, GraduationCap, Flag, ClipboardList } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import {
  fetchAgpTrackStatus,
  fetchAgpEnrollment,
  fetchAgpCohortSummary,
  fetchAgpCoaching,
  fetchAgpKpiScorecard,
  type AgpTrackStatus,
  type AgpEnrollment,
  type AgpCohortSummary,
  type AgpCoachingSession,
  type AgpKpiRow,
} from "@/lib/api/agp";
import { AgpCohortBars } from "@/components/charts/agp-cohort-bars";
import { KpiGauge } from "@/components/charts/kpi-gauge";
import { KpiTargetActual } from "@/components/charts/kpi-target-actual";
import { AiInsightSummary, type AiInsightData } from "@/components/patterns/ai-insight-summary";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { colors, severity as sevTokens } from "@/styles/tokens";
import { formatCurrency } from "@/lib/utils";

const BAND_VARIANT: Record<string, "success" | "warning" | "destructive"> = {
  on_track: "success", attention: "warning", urgent: "warning", critical: "destructive",
};

// Milestone progress status -> Completed / In Progress / Not Started (CLAUDE.md 9.5).
const MILESTONE_BUCKET: Record<string, { label: string; color: string }> = {
  COMPLETED: { label: "Completed", color: colors.positive },
  ON_TRACK: { label: "In Progress", color: colors.primary },
  AT_RISK: { label: "In Progress", color: colors.warning },
  IN_PROGRESS: { label: "In Progress", color: colors.primary },
  UPCOMING: { label: "Not Started", color: colors.text.muted },
  NOT_STARTED: { label: "Not Started", color: colors.text.muted },
};

interface MilestoneRow { milestone_progress_id: string; due_date: string | null; status: string | null; attainment_pct: number | null; days_remaining: number | null }

function fmtKpi(v: number | null, unit: string | null): string {
  if (v === null || v === undefined) return "—";
  if (unit === "USD") return formatCurrency(v, { compact: true });
  if (unit === "PERCENT") return `${v}%`;
  return String(v);
}

export function AgpWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [track, setTrack] = useState<AgpTrackStatus | null>(null);
  const [enrollment, setEnrollment] = useState<AgpEnrollment | null>(null);
  const [cohort, setCohort] = useState<AgpCohortSummary | null>(null);
  const [coaching, setCoaching] = useState<AgpCoachingSession[]>([]);
  const [kpis, setKpis] = useState<AgpKpiRow[]>([]);
  const [milestones, setMilestones] = useState<MilestoneRow[]>([]);
  const [ai, setAi] = useState<AiInsightData | null>(null);
  const [selectedKpi, setSelectedKpi] = useState<string | null>(null);

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
    const cohortScope = shell.scopeType === "Advisor" ? "FIRM" : shell.scopeType.toUpperCase();
    const cohortScopeId = shell.scopeType === "Advisor" ? "F001" : shell.scopeId;
    setAi(null);
    const [t, e, c, ch, sc] = await Promise.all([
      fetchAgpTrackStatus(advisorId),
      fetchAgpEnrollment(advisorId),
      fetchAgpCohortSummary(cohortScope, cohortScopeId),
      fetchAgpCoaching(advisorId),
      fetchAgpKpiScorecard(advisorId),
    ]);
    setTrack(t);
    const enr = e.enrollments[0] ?? null;
    setEnrollment(enr);
    setCohort(c);
    setCoaching(ch.coaching_sessions ?? []);
    setKpis(sc.scorecard ?? []);
    setSelectedKpi(sc.scorecard?.[0]?.kpi_id ?? null);
    // program milestones for the enrolled advisor
    if (enr?.enrollment_id) {
      apiClient.get<{ timeline: MilestoneRow[] }>(`/agp/milestones/${enr.enrollment_id}`).then((m) => setMilestones(m.timeline ?? [])).catch(() => setMilestones([]));
    } else setMilestones([]);
    // AI KPI insights (reuse the grounded advisor insight engine)
    apiClient.get<{ insight: AiInsightData }>(`/advisor/360/${advisorId}/ai`).then((r) => setAi(r.insight)).catch(() => setAi(null));
  }, [advisorId, shell.scopeType, shell.scopeId, shell.refreshNonce]);

  useEffect(() => { void load(); }, [load]);

  const advisorName = advisors.find((a) => a.advisor_id === advisorId)?.advisor_name ?? advisorId;
  const ms = track?.current_milestone;
  const comps = track?.components;
  const selected = kpis.find((k) => k.kpi_id === selectedKpi) ?? kpis[0] ?? null;

  if (track && !track.enrolled) {
    return (
      <div className="space-y-3">
        <h2 className="text-[22px] font-black">{advisorName} · AGP Goals &amp; Coaching</h2>
        <Card><CardContent className="p-8 text-center text-[13px] text-muted-foreground">
          {advisorName} is not enrolled in an AGP program. Select an enrolled advisor from the breadcrumb or the picker to view goals, KPIs and coaching.
        </CardContent></Card>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Advisor Growth Program</Badge>
          <h2 className="mt-2 text-[22px] font-black">{advisorName} · AGP Goals &amp; Coaching</h2>
          <p className="text-[12px] text-muted-foreground">
            Real AGP-004 on/off-track scoring, per-KPI Target-vs-Current attainment, milestone status and cohort rollup — scope-aware via the breadcrumb.
          </p>
        </div>
        <select className="h-8 rounded-lg border border-border bg-background px-2 text-[12px]" value={advisorId} onChange={(e) => setAdvisorId(e.target.value)}>
          {advisors.length === 0 && <option value={advisorId}>{advisorId}</option>}
          {advisors.map((a) => <option key={a.advisor_id} value={a.advisor_id}>{a.advisor_name ?? a.advisor_id}</option>)}
        </select>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="AGP Risk Score" value={track ? String(track.score) : "—"} icon={Gauge} iconColor={colors.aiAccent} />
        <KpiStatCard label="Milestone Attainment" value={ms ? `${ms.attainment_pct}%` : "—"} icon={Target} iconColor={colors.primary} />
        <KpiStatCard label="Days To Milestone" value={ms ? String(ms.days_remaining) : "—"} icon={CalendarClock} iconColor={colors.warning} />
        <KpiStatCard label="Program Month" value={enrollment ? `${enrollment.current_program_month}/24` : "—"} icon={Flag} iconColor={colors.positive} />
      </div>

      {/* KPI gauges/meters — visual (CLAUDE.md 9.12) */}
      <Card>
        <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Gauge className="h-4 w-4 text-primary" /> KPI Attainment Meters</CardTitle></CardHeader>
        <CardContent className="p-3">
          <div className="flex flex-wrap justify-around gap-4">
            {kpis.map((k) => (
              <KpiGauge key={k.kpi_id} label={k.kpi_name} pct={k.attainment_pct} onTrack={(k.status ?? "").toUpperCase() === "ON_TRACK"} />
            ))}
            {kpis.length === 0 && <div className="p-6 text-[12px] text-muted-foreground">No KPI measurements.</div>}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]"><Gauge className="h-4 w-4 text-primary" /> Track Status (AGP-004)</CardTitle>
            {track && <Badge variant={BAND_VARIANT[track.band] ?? "glass"}>{track.band.replace("_", " ")}</Badge>}
          </CardHeader>
          <CardContent className="space-y-3 p-3">
            {comps && (
              <>
                <div className="flex items-baseline gap-2">
                  <span className="text-[28px] font-black" style={{ color: colors.text.primary }}>{track!.score}</span>
                  <span className="text-[12px] text-muted-foreground">risk score (0=on-track, 100=critical)</span>
                </div>
                <div className="space-y-2">
                  {([
                    ["Attainment Gap", comps.attainment_gap, comps.weights.attainment_gap],
                    ["Time Pressure", comps.time_pressure, comps.weights.time_pressure],
                    ["CRM Execution Risk", comps.crm_execution_risk, comps.weights.crm_execution_risk],
                  ] as const).map(([label, value, weight]) => (
                    <div key={label}>
                      <div className="flex justify-between text-[11px]">
                        <span className="text-muted-foreground">{label} <span className="opacity-60">· w{weight}</span></span>
                        <span className="font-mono">{value}</span>
                      </div>
                      <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full" style={{ width: `${Math.min(100, value)}%`, backgroundColor: value > 50 ? sevTokens.urgent.fg : colors.primary }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="rounded-xl border bg-good-soft p-2 text-[11px] text-muted-foreground">
                  <span className="font-semibold text-foreground">Explanation · </span>{track!.explanation}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><CalendarClock className="h-4 w-4 text-primary" /> Current Milestone &amp; Enrollment</CardTitle></CardHeader>
          <CardContent className="space-y-3 p-3 text-[12px]">
            {ms && (
              <div className="rounded-xl border p-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold">Milestone {ms.milestone_progress_id}</span>
                  <Badge variant="glass">{ms.status}</Badge>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full" style={{ width: `${ms.attainment_pct}%`, backgroundColor: colors.positive }} />
                </div>
                <div className="mt-1 flex justify-between text-muted-foreground">
                  <span>{ms.attainment_pct}% attained</span>
                  <span>due {ms.due_date} · {ms.days_remaining}d</span>
                </div>
              </div>
            )}
            {enrollment && (
              <div className="grid grid-cols-2 gap-2">
                <Info label="Cohort" value={enrollment.cohort} />
                <Info label="Status" value={enrollment.status} />
                <Info label="Months Elapsed" value={String(enrollment.months_elapsed)} />
                <Info label="Months Remaining" value={String(enrollment.months_remaining)} />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Goals & KPIs table + drill-in Target-vs-Actual */}
      <Card>
        <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Target className="h-4 w-4 text-primary" /> Goals &amp; KPIs — Target vs Current</CardTitle></CardHeader>
        <CardContent className="p-3">
          <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b text-left" style={{ borderColor: colors.surface.border }}>
                    {["KPI", "Target", "Current", "Progress", "Status"].map((h) => (
                      <th key={h} className="px-2 py-2 text-[11px] font-semibold uppercase tracking-[0.05em]" style={{ color: colors.text.muted }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {kpis.map((k) => {
                    const onTrack = (k.status ?? "").toUpperCase() === "ON_TRACK";
                    const isSel = k.kpi_id === selected?.kpi_id;
                    return (
                      <tr key={k.kpi_id} onClick={() => setSelectedKpi(k.kpi_id)} className="cursor-pointer border-b last:border-0" style={{ borderColor: colors.surface.border, backgroundColor: isSel ? colors.surface.canvas : undefined }}>
                        <td className="px-2 py-2 text-[12px] font-semibold" style={{ color: colors.text.primary }}>{k.kpi_name}</td>
                        <td className="px-2 py-2 font-mono text-[12px]" style={{ color: colors.text.secondary }}>{fmtKpi(k.target, k.unit)}</td>
                        <td className="px-2 py-2 font-mono text-[12px]" style={{ color: colors.text.primary }}>{fmtKpi(k.current, k.unit)}</td>
                        <td className="px-2 py-2">
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-16 overflow-hidden rounded-full" style={{ backgroundColor: colors.surface.border }}>
                              <div className="h-full rounded-full" style={{ width: `${Math.min(100, k.attainment_pct)}%`, backgroundColor: onTrack ? colors.positive : colors.negative }} />
                            </div>
                            <span className="font-mono text-[11px]" style={{ color: colors.text.muted }}>{k.attainment_pct}%</span>
                          </div>
                        </td>
                        <td className="px-2 py-2">
                          <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.04em]" style={{ color: onTrack ? "#0F766E" : "#B91C1C", backgroundColor: onTrack ? "#F0FDFA" : "#FEF2F2" }}>
                            {onTrack ? "On Track" : "Off Track"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div>
              {selected ? (
                <>
                  <div className="mb-1 text-[12px] font-semibold" style={{ color: colors.text.primary }}>{selected.kpi_name} · Target vs Actual over milestones</div>
                  <KpiTargetActual data={selected.history.map((h) => ({ label: h.label, target: h.target, actual: h.actual }))} unit={selected.unit} />
                </>
              ) : <div className="p-6 text-[12px] text-muted-foreground">Select a KPI.</div>}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Program milestones with Completed / In Progress / Not Started */}
      <Card>
        <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Flag className="h-4 w-4 text-primary" /> Program Milestones</CardTitle></CardHeader>
        <CardContent className="p-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
            {milestones.map((m) => {
              const b = MILESTONE_BUCKET[(m.status ?? "").toUpperCase()] ?? { label: m.status ?? "—", color: colors.text.muted };
              return (
                <div key={m.milestone_progress_id} className="rounded-lg border p-2" style={{ borderColor: colors.surface.border }}>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px]" style={{ color: colors.text.muted }}>{m.due_date}</span>
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: b.color }} />
                  </div>
                  <div className="mt-1 text-[16px] font-black" style={{ color: colors.text.primary }}>{m.attainment_pct ?? 0}%</div>
                  <div className="text-[10px] font-semibold" style={{ color: b.color }}>{b.label}</div>
                </div>
              );
            })}
            {milestones.length === 0 && <div className="p-4 text-[12px] text-muted-foreground">No milestone timeline.</div>}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 xl:grid-cols-[1.1fr_.9fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]"><Users className="h-4 w-4 text-primary" /> Cohort Milestone Rollup</CardTitle>
            {cohort && <span className="text-[10px] text-muted-foreground">{cohort.enrollment_count} enrollments · {cohort.scope.scope_type}</span>}
          </CardHeader>
          <CardContent className="p-3">
            {cohort && cohort.milestone_summary.length > 0 ? <AgpCohortBars data={cohort.milestone_summary} /> : <div className="p-8 text-center text-[12px] text-muted-foreground">No cohort data.</div>}
          </CardContent>
        </Card>

        {ai ? <AiInsightSummary data={ai} title="AI KPI Insights" /> : <div className="h-[320px] animate-pulse rounded-xl bg-slate-100" />}
      </div>

      <Card>
        <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><GraduationCap className="h-4 w-4 text-primary" /> Coaching Sessions</CardTitle></CardHeader>
        <CardContent className="grid gap-2 p-3 md:grid-cols-2 xl:grid-cols-3">
          {coaching.length === 0 && <div className="p-4 text-center text-[12px] text-muted-foreground">No coaching sessions.</div>}
          {coaching.map((s) => {
            let items: string[] = [];
            try { items = s.action_items_json ? JSON.parse(s.action_items_json) : []; } catch { items = []; }
            return (
              <div key={s.session_id} className="rounded-xl border bg-background/80 p-3 text-[12px]" style={{ borderColor: colors.surface.border }}>
                <div className="flex items-center justify-between">
                  <span className="font-bold">{s.session_type?.replace("_", " ")}</span>
                  <span className="font-mono text-[11px] text-muted-foreground">{s.session_date}</span>
                </div>
                <p className="mt-1 text-muted-foreground">{s.summary}</p>
                {items.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {items.map((it, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <ClipboardList className="mt-0.5 h-3 w-3 shrink-0" style={{ color: colors.primary }} />
                        <span style={{ color: colors.text.secondary }}>{it}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-background/70 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}
