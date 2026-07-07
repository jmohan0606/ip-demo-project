"use client";
import { useCallback, useEffect, useState } from "react";
import { GraduationCap, Star, CheckSquare, ClipboardCheck, ClipboardList, Plus, UserCog } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import {
  fetchCoaching, fetchCoachingTasks, fetchTaskCatalog, createCoachingTask, updateCoachingTaskStatus,
  type CoachingReviewData, type CoachingTask, type TaskTemplate, type UserRef,
} from "@/lib/api/coaching";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { colors, type } from "@/styles/tokens";

const STATUS_VARIANT: Record<string, "success" | "warning" | "glass"> = {
  COMPLETED: "success",
  SCHEDULED: "warning",
  PENDING: "warning",
};

const PRIORITY_COLOR: Record<string, string> = { HIGH: colors.negative, MEDIUM: colors.warning, LOW: colors.positive };
const TASK_STATUS_COLOR: Record<string, string> = { OPEN: colors.primary, IN_PROGRESS: colors.warning, COMPLETED: colors.positive };

function userLabel(u?: UserRef | null): string {
  if (!u || !u.display_name) return "—";
  return u.role_code ? `${u.display_name} (${u.role_code})` : u.display_name;
}

export function CoachingReviewsWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [data, setData] = useState<CoachingReviewData | null>(null);
  const [tasks, setTasks] = useState<CoachingTask[]>([]);
  const [catalog, setCatalog] = useState<TaskTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<number>(0);
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    apiClient
      .get<{ advisors: Array<{ advisor_id: string; advisor_name: string | null }> }>("/advisor/list")
      .then((r) => setAdvisors(r.advisors))
      .catch(() => setAdvisors([]));
    fetchTaskCatalog().then(setCatalog).catch(() => setCatalog([]));
  }, []);

  useEffect(() => {
    if (shell.scopeType === "Advisor") setAdvisorId(shell.scopeId);
    else resolveScope(shell.scopeType, shell.scopeId).then((r) => setAdvisorId(r.advisor_ids[0] ?? "A001")).catch(() => undefined);
  }, [shell.scopeType, shell.scopeId]);

  const loadTasks = useCallback(async () => {
    fetchCoachingTasks(advisorId).then((t) => setTasks(t.tasks)).catch(() => setTasks([]));
  }, [advisorId]);

  const load = useCallback(async () => {
    setData(await fetchCoaching(advisorId));
    await loadTasks();
  }, [advisorId, loadTasks]);

  useEffect(() => {
    void load();
  }, [load]);

  const assignTask = async () => {
    const tpl = catalog[selectedTemplate];
    if (!tpl) return;
    setAssigning(true);
    try {
      const today = new Date().toISOString().slice(0, 10);
      await createCoachingTask({ advisor_id: advisorId, title: tpl.title, category: tpl.category, instruction: tpl.instruction, priority: tpl.priority, created_date: today });
      await loadTasks();
    } finally {
      setAssigning(false);
    }
  };

  const cycleStatus = async (task: CoachingTask) => {
    const next = task.status === "OPEN" ? "IN_PROGRESS" : task.status === "IN_PROGRESS" ? "COMPLETED" : "OPEN";
    const today = new Date().toISOString().slice(0, 10);
    await updateCoachingTaskStatus(task.task_id, next, next === "COMPLETED" ? today : null);
    await loadTasks();
  };

  const s = data?.summary;
  const advisorName = data?.advisor_name ?? advisorId;
  const openTasks = tasks.filter((t) => t.status !== "COMPLETED").length;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Coaching &amp; Reviews</Badge>
          <h2 className={`mt-2 ${type.pageTitle}`}>{advisorName} · Coaching History</h2>
          <p className="text-[12px] text-muted-foreground">
            Real coaching sessions and manager reviews from the graph — the human side of the AGP
            loop, with action items and ratings.
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
        <KpiStatCard label="Coaching Sessions" value={String(s?.session_count ?? "—")} icon={GraduationCap} iconColor={colors.primary} />
        <KpiStatCard label="Manager Reviews" value={String(s?.review_count ?? "—")} icon={ClipboardCheck} iconColor={colors.aiAccent} />
        <KpiStatCard label="Avg Review Rating" value={s?.avg_rating != null ? `${s.avg_rating.toFixed(1)}/5` : "—"} icon={Star} iconColor={colors.warning} />
        <KpiStatCard label="Open Coaching Tasks" value={String(openTasks)} icon={ClipboardList} iconColor={colors.positive} />
      </div>

      {/* Manager-assigns-task feature (CLAUDE.md 9.5): assign from catalog, persist, track, feed AI */}
      <Card data-story-target="coaching-tasks">
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]"><UserCog className="h-4 w-4 text-primary" /> Manager · Assign Coaching Task</CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-[260px] flex-1">
              <label className="text-[10px] font-semibold uppercase tracking-[0.05em]" style={{ color: colors.text.muted }}>Task template</label>
              <select className="mt-1 h-9 w-full rounded-lg border border-border bg-background px-2 text-[12px]" value={selectedTemplate} onChange={(e) => setSelectedTemplate(Number(e.target.value))}>
                {catalog.map((t, i) => <option key={i} value={i}>{t.title} · {t.category} · {t.priority}</option>)}
              </select>
              {catalog[selectedTemplate] && <p className="mt-1 text-[11px] text-muted-foreground">{catalog[selectedTemplate].instruction}</p>}
            </div>
            <button onClick={assignTask} disabled={assigning || catalog.length === 0} className="inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-[12px] font-semibold text-white disabled:opacity-50" style={{ backgroundColor: colors.primary }}>
              <Plus className="h-4 w-4" /> {assigning ? "Assigning…" : `Assign to ${advisorName}`}
            </button>
          </div>

          <div className="mt-3 space-y-1.5">
            {tasks.length === 0 && <div className="p-3 text-center text-[12px] text-muted-foreground">No coaching tasks assigned yet.</div>}
            {tasks.map((t) => (
              <div key={t.task_id} className="flex flex-wrap items-center gap-2 rounded-lg border p-2.5" style={{ borderColor: colors.surface.border }}>
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: TASK_STATUS_COLOR[t.status] ?? colors.text.muted }} />
                <div className="min-w-[200px] flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-semibold" style={{ color: colors.text.primary }}>{t.title}</span>
                    <span className="rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase" style={{ color: PRIORITY_COLOR[t.priority ?? ""] ?? colors.text.muted, backgroundColor: `${PRIORITY_COLOR[t.priority ?? ""] ?? colors.text.muted}14` }}>{t.priority}</span>
                    <span className="text-[10px]" style={{ color: colors.text.muted }}>{t.category}</span>
                  </div>
                  <p className="text-[11px]" style={{ color: colors.text.secondary }}>{t.instruction}</p>
                  <p className="text-[10px]" style={{ color: colors.text.muted }}>Assigned by {userLabel(t.assigned_by)}{t.due_date ? ` · due ${t.due_date}` : ""}</p>
                </div>
                <button onClick={() => cycleStatus(t)} className="rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.04em]" style={{ borderColor: colors.surface.border, color: TASK_STATUS_COLOR[t.status] ?? colors.text.muted }}>
                  {t.status.replace("_", " ")}
                </button>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10px] text-muted-foreground">Assigned tasks persist to the graph and are fed to the AI Assistant as coaching context for this advisor.</p>
        </CardContent>
      </Card>

      <div className="grid gap-3 xl:grid-cols-[1.3fr_.7fr]">
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <GraduationCap className="h-4 w-4 text-primary" /> Coaching Sessions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 p-3">
            {(data?.coaching_sessions ?? []).length === 0 && (
              <div className="p-6 text-center text-[12px] text-muted-foreground">No coaching sessions.</div>
            )}
            {(data?.coaching_sessions ?? []).map((session) => (
              <div key={session.session_id} className="rounded-xl border bg-background/80 p-3 text-[12px]">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold">{session.session_type?.replace("_", " ")}</span>
                    <Badge variant={STATUS_VARIANT[session.status ?? ""] ?? "glass"}>{session.status}</Badge>
                  </div>
                  <span className="font-mono text-[11px] text-muted-foreground">{session.session_date}</span>
                </div>
                <p className="mt-1 text-muted-foreground">{session.summary}</p>
                {session.action_items.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {session.action_items.map((item, i) => (
                      <li key={i} className="flex items-center gap-1.5">
                        <CheckSquare className="h-3 w-3 text-primary" />
                        {item}
                      </li>
                    ))}
                  </ul>
                )}
                <div className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                  <UserCog className="h-3 w-3" /> Coach {userLabel(session.coach)}
                  {session.next_session_date && <span>· next <span className="font-mono">{session.next_session_date}</span></span>}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <ClipboardCheck className="h-4 w-4 text-primary" /> Manager Reviews
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 p-3">
            {(data?.manager_reviews ?? []).length === 0 && (
              <div className="p-6 text-center text-[12px] text-muted-foreground">No reviews.</div>
            )}
            {(data?.manager_reviews ?? []).map((review) => (
              <div key={review.review_id} className="rounded-xl border bg-background/80 p-3 text-[12px]">
                <div className="flex items-center justify-between">
                  <span className="font-bold">{review.review_type?.replace("_", " ")}</span>
                  <span className="flex items-center gap-1">
                    {review.rating != null &&
                      Array.from({ length: 5 }).map((_, i) => (
                        <Star
                          key={i}
                          className="h-3 w-3"
                          fill={i < Math.round(review.rating!) ? "#F59E0B" : "none"}
                          color="#F59E0B"
                        />
                      ))}
                  </span>
                </div>
                <p className="mt-1 text-muted-foreground">{review.summary}</p>
                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                  <UserCog className="h-3 w-3" /> <span className="font-semibold" style={{ color: colors.text.secondary }}>{userLabel(review.reviewer)}</span>
                  · <span className="font-mono">{review.review_date}</span> ·{" "}
                  <Badge variant={STATUS_VARIANT[review.status ?? ""] ?? "glass"}>{review.status}</Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {data && (
        <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Evidence · </span>
          {data.evidence.source}
        </div>
      )}
    </div>
  );
}
