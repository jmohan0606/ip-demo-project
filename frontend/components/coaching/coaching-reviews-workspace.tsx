"use client";
import { useCallback, useEffect, useState } from "react";
import { GraduationCap, Star, CheckSquare, ClipboardCheck } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import { fetchCoaching, type CoachingReviewData } from "@/lib/api/coaching";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const STATUS_VARIANT: Record<string, "success" | "warning" | "glass"> = {
  COMPLETED: "success",
  SCHEDULED: "warning",
  PENDING: "warning",
};

export function CoachingReviewsWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [data, setData] = useState<CoachingReviewData | null>(null);

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
    setData(await fetchCoaching(advisorId));
  }, [advisorId]);

  useEffect(() => {
    void load();
  }, [load]);

  const s = data?.summary;
  const advisorName = data?.advisor_name ?? advisorId;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Coaching &amp; Reviews</Badge>
          <h2 className="mt-2 text-[22px] font-black">{advisorName} · Coaching History</h2>
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
        <KpiStatCard label="Coaching Sessions" value={String(s?.session_count ?? "—")} />
        <KpiStatCard label="Manager Reviews" value={String(s?.review_count ?? "—")} />
        <KpiStatCard label="Avg Review Rating" value={s?.avg_rating != null ? `${s.avg_rating.toFixed(1)}/5` : "—"} />
        <KpiStatCard
          label="Open Action Items"
          value={String(s?.open_action_items ?? "—")}
          delta={s ? `${s.total_action_items} total` : undefined}
          deltaPositive={s?.open_action_items === 0}
        />
      </div>

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
                {session.next_session_date && (
                  <div className="mt-2 text-[11px] text-muted-foreground">
                    Next session · <span className="font-mono">{session.next_session_date}</span> · coach {session.coach_user_id}
                  </div>
                )}
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
                <div className="mt-1 text-[11px] text-muted-foreground">
                  <span className="font-mono">{review.review_date}</span> · {review.reviewer_user_id} ·{" "}
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
