"use client";
import { useCallback, useEffect, useState } from "react";
import { Target, Gauge, CalendarClock, Users, GraduationCap } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import {
  fetchAgpTrackStatus,
  fetchAgpEnrollment,
  fetchAgpCohortSummary,
  fetchAgpCoaching,
  type AgpTrackStatus,
  type AgpEnrollment,
  type AgpCohortSummary,
  type AgpCoachingSession,
} from "@/lib/api/agp";
import { AgpCohortBars } from "@/components/charts/agp-cohort-bars";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { colors, severity as sevTokens } from "@/styles/tokens";

const BAND_VARIANT: Record<string, "success" | "warning" | "destructive"> = {
  on_track: "success",
  attention: "warning",
  urgent: "warning",
  critical: "destructive",
};

export function AgpWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [track, setTrack] = useState<AgpTrackStatus | null>(null);
  const [enrollment, setEnrollment] = useState<AgpEnrollment | null>(null);
  const [cohort, setCohort] = useState<AgpCohortSummary | null>(null);
  const [coaching, setCoaching] = useState<AgpCoachingSession[]>([]);

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
    const [t, e, c, ch] = await Promise.all([
      fetchAgpTrackStatus(advisorId),
      fetchAgpEnrollment(advisorId),
      fetchAgpCohortSummary(cohortScope, cohortScopeId),
      fetchAgpCoaching(advisorId),
    ]);
    setTrack(t);
    setEnrollment(e.enrollments[0] ?? null);
    setCohort(c);
    setCoaching(ch.coaching_sessions ?? []);
  }, [advisorId, shell.scopeType, shell.scopeId]);

  useEffect(() => {
    void load();
  }, [load]);

  const advisorName = advisors.find((a) => a.advisor_id === advisorId)?.advisor_name ?? advisorId;
  const ms = track?.current_milestone;
  const comps = track?.components;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Advisor Growth Program</Badge>
          <h2 className="mt-2 text-[22px] font-black">{advisorName} · AGP Goals &amp; Coaching</h2>
          <p className="text-[12px] text-muted-foreground">
            Real AGP-004 on/off-track scoring, milestone attainment and cohort rollup — the risk
            score is decomposed into weighted drivers with a plain-language explanation.
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
        <KpiStatCard label="AGP Risk Score" value={track ? String(track.score) : "—"} />
        <KpiStatCard label="Milestone Attainment" value={ms ? `${ms.attainment_pct}%` : "—"} />
        <KpiStatCard label="Days To Milestone" value={ms ? String(ms.days_remaining) : "—"} />
        <KpiStatCard label="Program Month" value={enrollment ? `${enrollment.current_program_month}/24` : "—"} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Gauge className="h-4 w-4 text-primary" /> Track Status (AGP-004)
            </CardTitle>
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
                  {(
                    [
                      ["Attainment Gap", comps.attainment_gap, comps.weights.attainment_gap],
                      ["Time Pressure", comps.time_pressure, comps.weights.time_pressure],
                      ["CRM Execution Risk", comps.crm_execution_risk, comps.weights.crm_execution_risk],
                    ] as const
                  ).map(([label, value, weight]) => (
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
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <CalendarClock className="h-4 w-4 text-primary" /> Current Milestone &amp; Enrollment
            </CardTitle>
          </CardHeader>
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

      <div className="grid gap-3 xl:grid-cols-[1.1fr_.9fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Users className="h-4 w-4 text-primary" /> Cohort Milestone Rollup
            </CardTitle>
            {cohort && <span className="text-[10px] text-muted-foreground">{cohort.enrollment_count} enrollments · {cohort.scope.scope_type}</span>}
          </CardHeader>
          <CardContent className="p-3">
            {cohort && cohort.milestone_summary.length > 0 ? (
              <AgpCohortBars data={cohort.milestone_summary} />
            ) : (
              <div className="p-8 text-center text-[12px] text-muted-foreground">No cohort data.</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <GraduationCap className="h-4 w-4 text-primary" /> Coaching Sessions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 p-3">
            {coaching.length === 0 && <div className="p-4 text-center text-[12px] text-muted-foreground">No coaching sessions.</div>}
            {coaching.map((s) => (
              <div key={s.session_id} className="rounded-xl border bg-background/80 p-2 text-[12px]">
                <div className="flex items-center justify-between">
                  <span className="font-bold">{s.session_type?.replace("_", " ")}</span>
                  <span className="font-mono text-[11px] text-muted-foreground">{s.session_date}</span>
                </div>
                <p className="text-muted-foreground">{s.summary}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
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
