"use client";

import { useCallback, useEffect, useState } from "react";

import { CheckCircle2, CircleCheck, PencilLine, MinusCircle, XCircle, TrendingUp, ShieldCheck, Layers, Zap } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { ImpactTrendChart, type ImpactPoint } from "@/components/charts/impact-trend-chart";
import LearningStateShowcase from "@/components/recommendations/learning-state-showcase";
import { OutcomeLearningPanel } from "@/components/recommendations/outcome-learning-panel";
import { AiContentCard } from "@/components/patterns/ai-content-card";
import { AiCardSkeleton, ErrorState } from "@/components/patterns/async-state";
import { Skeleton } from "@/components/ui/skeleton";
import { EvidenceTracePills } from "@/components/patterns/evidence-trace";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { SeverityBadge } from "@/components/patterns/severity-badge";
import { ProductSystemLabel } from "@/components/patterns/product-system-label";
import { AdvisorSelector } from "@/components/status/advisor-selector";
import { apiClient } from "@/lib/api/client";
import { useScopedAdvisor } from "@/lib/hooks/use-scoped-advisor";
import { colors, type } from "@/styles/tokens";

// Action-family category tags: color + icon (CLAUDE.md 9.5).
const FAMILY_META: Record<string, { label: string; color: string; icon: LucideIcon }> = {
  MANAGED_MIX: { label: "Managed Mix", color: colors.primary, icon: Layers },
  RETENTION: { label: "Retention", color: colors.warning, icon: ShieldCheck },
  CRM_EXECUTION: { label: "CRM Execution", color: colors.aiAccent, icon: Zap },
};
const familyMeta = (f: string) => FAMILY_META[f] ?? { label: f?.replace("_", " ") ?? "Action", color: colors.text.muted, icon: TrendingUp };

// Color-coded feedback actions (green accept/complete, amber modify, red reject).
const ACTION_META: Record<string, { color: string; bg: string; icon: LucideIcon }> = {
  ACCEPT: { color: "#0F766E", bg: "#F0FDFA", icon: CheckCircle2 },
  COMPLETE: { color: "#065F46", bg: "#ECFDF5", icon: CircleCheck },
  MODIFY: { color: "#B45309", bg: "#FFFBEB", icon: PencilLine },
  IGNORE: { color: "#475569", bg: "#F1F5F9", icon: MinusCircle },
  REJECT: { color: "#B91C1C", bg: "#FEF2F2", icon: XCircle },
};

interface ImpactTrend {
  event_count: number;
  trend: ImpactPoint[];
  totals: {
    accepted: number; implemented: number; rejected: number; modified: number; ignored: number;
    cumulative_reward: number; captured_impact: number;
  };
  final_weights: Array<{ family: string; weight: number; events: number }>;
}

interface Recommendation {
  recommendation_id: string;
  title: string;
  action_text: string;
  action_family: string;
  base_priority_score: number;
  learning_weight: number;
  priority_score: number;
  severity: string;
  confidence: number;
  estimated_revenue_impact: number;
  opportunity_id: string;
  prediction_id: string | null;
  playbook_id: string | null;
  // Section 13.1 lifecycle fields (authoritative, server-driven)
  status?: string;
  status_note?: string | null;
  allowed_actions?: string[];
  terminal?: boolean;
  compliance?: { status: string; warnings: string[] };
}

interface AddressedOpportunity {
  opportunity_id: string;
  category: string;
  severity?: string;
  addressed_by?: string;
  completed_ts?: string;
  note?: string;
}

interface LifecycleCounts {
  open: number; accepted: number; in_progress: number; completed: number;
  rejected: number; ignored: number; modified: number;
}

interface GenerateResponse {
  advisor_id: string;
  recommendations: Recommendation[];
  learning_weights: Array<{ family: string; weight: number; feedback_count: number }>;
  feature_snapshot_id: string;
  lifecycle_counts?: LifecycleCounts;
  addressed_opportunities?: AddressedOpportunity[];
}

const FEEDBACK_ACTIONS = ["ACCEPT", "COMPLETE", "MODIFY", "IGNORE", "REJECT"] as const;

export function RecommendationsWorkspace() {
  const { advisorId, refreshNonce } = useScopedAdvisor();
  const [data, setData] = useState<GenerateResponse | null>(null);
  const [impact, setImpact] = useState<ImpactTrend | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastEffect, setLastEffect] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Optimistic per-recommendation status after a feedback click (12.8 minimum
  // visible-feedback fix; §13 replaces this with the persisted state machine).
  const [actedStatus, setActedStatus] = useState<Record<string, string>>({});

  const generate = useCallback(async () => {
    if (!advisorId) return;
    setBusy(true);
    setError(null);
    try {
      setData(await apiClient.post<GenerateResponse>(`/recommendations/generate/${advisorId}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate recommendations");
    } finally {
      setBusy(false);
    }
  }, [advisorId, refreshNonce]);

  useEffect(() => {
    void generate();
  }, [generate]);

  const loadImpact = useCallback(async () => {
    await apiClient
      .get<ImpactTrend>("/feedback-learning/impact-trend")
      .then(setImpact)
      .catch(() => setImpact(null));
  }, []);

  useEffect(() => {
    void loadImpact();
  }, [loadImpact]);

  // Map a feedback action to the terminal status label it produces (12.8 visible status).
  const STATUS_FOR_ACTION: Record<string, string> = {
    ACCEPT: "ACCEPTED", COMPLETE: "COMPLETED", MODIFY: "IN PROGRESS", IGNORE: "IGNORED", REJECT: "REJECTED",
  };

  const submitFeedback = async (rec: Recommendation, action: string) => {
    setBusy(true);
    try {
      const result = await apiClient.post<{ effect: string; lifecycle?: { to_status: string; impact?: { impact_amount: number } | null } }>(
        "/feedback-learning/submit", { recommendation_id: rec.recommendation_id, action, action_family: rec.action_family });
      const to = result.lifecycle?.to_status ?? STATUS_FOR_ACTION[action] ?? action;
      setActedStatus((prev) => ({ ...prev, [rec.recommendation_id]: to }));
      const impactTxt = result.lifecycle?.impact ? ` Impact +$${Math.round(result.lifecycle.impact.impact_amount).toLocaleString()} recorded — see the Impact Ledger.` : "";
      setLastEffect(`You ${action.toLowerCase()}ed "${rec.title}" → status ${to}. ${result.effect}${impactTxt}`);
      // Re-generate (statuses are now server-authoritative) + refresh impact trend.
      await Promise.all([generate(), loadImpact()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Feedback failed");
    } finally {
      setBusy(false);
    }
  };

  // Section 13.1: pure lifecycle transition (Start) — no learning signal.
  const transitionRec = async (rec: Recommendation, action: string) => {
    setBusy(true);
    try {
      const lc = await apiClient.post<{ to_status: string }>(`/recommendations/${rec.recommendation_id}/transition`, { action, actor_id: advisorId ?? undefined });
      setActedStatus((prev) => ({ ...prev, [rec.recommendation_id]: lc.to_status }));
      setLastEffect(`Started "${rec.title}" → status ${lc.to_status}.`);
      await generate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transition failed");
    } finally {
      setBusy(false);
    }
  };

  const recs = data?.recommendations ?? [];
  const totalImpact = recs.reduce((sum, rec) => sum + (rec.estimated_revenue_impact || 0), 0);

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div className="flex items-center justify-between">
        <div>
          <ProductSystemLabel />
          <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>
            Opportunities &amp; Recommendations
          </h1>
          <p className={type.body} style={{ color: colors.text.secondary }}>
            AI next-best-actions for advisor {advisorId} — ranked by severity-composed priority × learned family weight.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <AdvisorSelector />
          <button
            onClick={() => void generate()}
            disabled={busy}
            className="rounded-lg px-3 py-1.5 text-[13px] font-semibold text-white disabled:opacity-50"
            style={{ backgroundColor: colors.primary }}
          >
            {busy ? "Working…" : "Regenerate"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiStatCard label="Open recommendations" value={String(recs.length)} icon={TrendingUp} iconColor={colors.primary} />
        <KpiStatCard label="Estimated impact" value={`$${Math.round(totalImpact).toLocaleString()}`} icon={Zap} iconColor={colors.positive} />
        <KpiStatCard label="Feature snapshot" value={data?.feature_snapshot_id?.slice(0, 14) ?? "—"} icon={Layers} iconColor={colors.aiAccent} />
        <KpiStatCard label="Learning families" value={String(data?.learning_weights.length ?? 0)} icon={ShieldCheck} iconColor={colors.warning} />
      </div>

      {/* Feedback-outcome summary cards: accepted / completed / in-progress / rejected (9.5) */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {(() => {
          // Section 13.1: real per-advisor lifecycle counts from the server (persisted),
          // no longer the 12.8 optimistic session overlay.
          const lc = data?.lifecycle_counts;
          const accepted = lc?.accepted ?? 0;
          const implemented = lc?.completed ?? 0;
          const inProgress = lc?.in_progress ?? 0;
          const rejected = lc?.rejected ?? 0;
          const ignored = lc?.ignored ?? 0;
          const total = accepted + implemented + inProgress + rejected + ignored + (lc?.open ?? 0) + (lc?.modified ?? 0);
          const pct = (n: number) => (total ? `${Math.round((n / total) * 100)}%` : "—");
          const cards = [
            { label: "Accepted", n: accepted, color: colors.positive, bg: "#F0FDFA", icon: CheckCircle2 },
            { label: "Completed", n: implemented, color: "#059669", bg: "#ECFDF5", icon: CircleCheck },
            { label: "In Progress", n: inProgress, color: colors.warning, bg: "#FFFBEB", icon: PencilLine },
            { label: "Rejected", n: rejected, color: colors.negative, bg: "#FEF2F2", icon: XCircle },
          ];
          return cards.map((c) => (
            <div key={c.label} className="flex items-center gap-3 rounded-xl border bg-white px-4 py-3 shadow-sm" style={{ borderColor: colors.surface.border }}>
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full" style={{ backgroundColor: c.bg, color: c.color }}>
                <c.icon style={{ width: 18, height: 18 }} />
              </span>
              <div>
                <div className={type.label} style={{ color: colors.text.muted }}>{c.label}</div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-[20px] font-black" style={{ color: colors.text.primary }}>{c.n}</span>
                  <span className="text-[11px] font-semibold" style={{ color: c.color }}>{pct(c.n)}</span>
                </div>
              </div>
            </div>
          ));
        })()}
      </div>

      <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Recommendation impact</h2>
            <p className={type.data} style={{ color: colors.text.muted }}>
              Accepted / implemented / rejected as the real feedback loop is applied across the live
              recommendation set — the same reward signal that re-ranks the queue.
            </p>
          </div>
          {impact ? (
            <div className="flex gap-4">
              <div className="text-right">
                <div className={type.label} style={{ color: colors.text.muted }}>Captured impact</div>
                <div className="font-mono text-[16px] font-bold" style={{ color: colors.positive }}>
                  ${Math.round(impact.totals.captured_impact).toLocaleString()}
                </div>
              </div>
              <div className="text-right">
                <div className={type.label} style={{ color: colors.text.muted }}>Net reward</div>
                <div className="font-mono text-[16px] font-bold" style={{ color: colors.text.primary }}>
                  {impact.totals.cumulative_reward.toFixed(1)}
                </div>
              </div>
            </div>
          ) : null}
        </div>
        {impact && impact.trend.length ? (
          <div className="mt-2">
            <ImpactTrendChart data={impact.trend} />
            <div className="mt-2 flex flex-wrap gap-2">
              {impact.final_weights.map((w) => (
                <span
                  key={w.family}
                  className="rounded-md border px-2 py-1 text-[11px]"
                  style={{ borderColor: colors.surface.border, color: colors.text.secondary }}
                >
                  {w.family} weight{" "}
                  <span className="font-mono font-bold" style={{ color: w.weight >= 1 ? colors.positive : colors.negative }}>
                    {w.weight.toFixed(2)}
                  </span>{" "}
                  ({w.events} events)
                </span>
              ))}
            </div>
          </div>
        ) : (
          <Skeleton className="mt-2 h-[240px]" />
        )}
      </div>

      {lastEffect ? (
        <div
          className="rounded-lg border px-3 py-2 text-[12px]"
          style={{ borderColor: "#C7D2FE", backgroundColor: "#EEF2FF", color: colors.aiAccent }}
        >
          <span className="font-bold uppercase tracking-wide">What changed · </span>{lastEffect}
        </div>
      ) : null}
      {error && recs.length === 0 ? (
        <ErrorState message="Couldn't generate recommendations for this advisor." onRetry={() => void generate()} />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">{error}</div>
      ) : null}

      <div className="space-y-3">
        {busy && recs.length === 0 && !error
          ? Array.from({ length: 3 }).map((_, i) => <AiCardSkeleton key={i} />)
          : null}
        {recs.map((rec, index) => (
          <div key={rec.recommendation_id} data-story-target={index === 0 ? "rec-card-top" : undefined}>
          <AiContentCard
            title={`#${index + 1} · ${rec.title}`}
            footer={
              <div className="flex flex-wrap items-center justify-between gap-2">
                <EvidenceTracePills
                  items={[
                    { kind: "opp", id: rec.opportunity_id },
                    { kind: "pred", id: rec.prediction_id },
                    { kind: "features", id: data?.feature_snapshot_id },
                    { kind: "playbook", id: rec.playbook_id },
                  ]}
                />
                <div className="flex flex-wrap gap-1.5">
                  {/* Section 13.1: START appears only when the server allows it (ACCEPTED/IN_PROGRESS). */}
                  {(rec.allowed_actions ?? []).includes("start") && (
                    <button
                      onClick={() => void transitionRec(rec, "start")}
                      disabled={busy}
                      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold uppercase tracking-wide disabled:opacity-50"
                      style={{ color: colors.warning, backgroundColor: "#FFFBEB", border: `1px solid ${colors.warning}33` }}
                    >
                      <PencilLine style={{ width: 12, height: 12 }} /> START
                    </button>
                  )}
                  {FEEDBACK_ACTIONS.map((action) => {
                    const m = ACTION_META[action];
                    const Icon = m.icon;
                    // Server-driven enablement: only enabled when this action is allowed
                    // for the rec's current status ([] ⇒ terminal ⇒ all disabled).
                    const allowed = rec.allowed_actions ?? ["accept", "complete", "modify", "ignore", "reject"];
                    const enabled = allowed.includes(action.toLowerCase());
                    return (
                      <button
                        key={action}
                        onClick={() => void submitFeedback(rec, action)}
                        disabled={busy || !enabled}
                        title={!enabled ? `Not available for status ${rec.status ?? "OPEN"}` : undefined}
                        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold uppercase tracking-wide disabled:cursor-not-allowed disabled:opacity-40"
                        style={{ color: m.color, backgroundColor: m.bg, border: `1px solid ${m.color}33` }}
                      >
                        <Icon style={{ width: 12, height: 12 }} /> {action}
                      </button>
                    );
                  })}
                </div>
              </div>
            }
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                  {(() => { const m = familyMeta(rec.action_family); const Icon = m.icon; return (
                    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.04em]" style={{ color: m.color, backgroundColor: `${m.color}14` }}>
                      <Icon style={{ width: 12, height: 12 }} /> {m.label}
                    </span>
                  ); })()}
                  {(() => {
                    // Prefer the server-authoritative status; fall back to optimistic.
                    const raw = (rec.status && rec.status !== "OPEN" ? rec.status : actedStatus[rec.recommendation_id]) || "";
                    const st = raw.toUpperCase().replace("_", " ");
                    if (!st || st === "OPEN") return null;
                    const done = st === "ACCEPTED" || st === "COMPLETED";
                    const bad = st === "REJECTED" || st === "IGNORED";
                    const c = done ? colors.positive : bad ? colors.negative : colors.warning;
                    return (
                      <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.04em]" style={{ color: c, backgroundColor: `${c}18`, border: `1px solid ${c}55` }}>
                        ● {st}
                      </span>
                    );
                  })()}
                  {rec.compliance && (() => {
                    const ok = rec.compliance.status === "PASSED";
                    const cc = ok ? colors.positive : colors.warning;
                    return (
                      <span data-story-target={index === 0 ? "rec-compliance-chip" : undefined}
                        title={rec.compliance.warnings.join(" · ") || "Compliance check passed"}
                        className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.04em]"
                        style={{ color: cc, backgroundColor: `${cc}14`, border: `1px solid ${cc}44` }}>
                        <ShieldCheck style={{ width: 11, height: 11 }} /> Compliance {rec.compliance.status}
                      </span>
                    );
                  })()}
                </div>
                <p className={type.body} style={{ color: colors.text.primary }}>{rec.action_text}</p>
                {rec.status_note && (
                  <p className={`mt-1 rounded-md px-2 py-1 ${type.data}`} style={{ color: "#065F46", backgroundColor: "#ECFDF5", border: "1px solid #A7F3D0" }}>
                    {rec.status_note} <a href="/impact-ledger" className="font-semibold underline">View in Impact Ledger →</a>
                  </p>
                )}
                <p className={`mt-1 ${type.data}`} style={{ color: colors.text.muted }}>
                  priority {rec.priority_score} = base {rec.base_priority_score} × learned weight {rec.learning_weight}
                  {" · "}confidence {(rec.confidence * 100).toFixed(0)}%
                  {" · "}est. impact ${Math.round(rec.estimated_revenue_impact).toLocaleString()}
                </p>
              </div>
              <SeverityBadge value={rec.severity} />
            </div>
          </AiContentCard>
          </div>
        ))}
        {recs.length === 0 && !busy ? (
          <p className={type.body} style={{ color: colors.text.muted }}>
            No open recommendations for this advisor.
          </p>
        ) : null}
      </div>

      {/* Section 13.5: opportunities addressed by a completed recommendation — no longer re-issued. */}
      {(data?.addressed_opportunities?.length ?? 0) > 0 && (
        <div className="rounded-xl border p-3" style={{ borderColor: "#A7F3D0", backgroundColor: "#F0FDF4" }}>
          <div data-story-target="addressed-section" className={`mb-1.5 ${type.label}`} style={{ color: "#065F46" }}>Addressed ({data!.addressed_opportunities!.length}) — completed, not regenerating</div>
          <ul className="space-y-1">
            {data!.addressed_opportunities!.map((a) => (
              <li key={a.opportunity_id} className={type.data} style={{ color: colors.text.secondary }}>
                <span className="font-mono text-[11px]" style={{ color: colors.text.muted }}>{a.opportunity_id}</span>
                {" · "}{a.note ?? `Completed ${(a.completed_ts ?? "").slice(0, 10)} by ${a.addressed_by}`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* RL feedback-loop showcase — how weights move with feedback over rounds (9.5, Fable-designed) */}
      <div data-story-target="learning-state"><LearningStateShowcase /></div>

      <OutcomeLearningPanel />
    </div>
  );
}
