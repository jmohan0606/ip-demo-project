"use client";

import { useCallback, useEffect, useState } from "react";

import { CheckCircle2, CircleCheck, PencilLine, MinusCircle, XCircle, TrendingUp, ShieldCheck, Layers, Zap } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { ImpactTrendChart, type ImpactPoint } from "@/components/charts/impact-trend-chart";
import LearningStateShowcase from "@/components/recommendations/learning-state-showcase";
import { OutcomeLearningPanel } from "@/components/recommendations/outcome-learning-panel";
import { AiContentCard } from "@/components/patterns/ai-content-card";
import { EvidenceTracePills } from "@/components/patterns/evidence-trace";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { SeverityBadge } from "@/components/patterns/severity-badge";
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
}

interface GenerateResponse {
  advisor_id: string;
  recommendations: Recommendation[];
  learning_weights: Array<{ family: string; weight: number; feedback_count: number }>;
  feature_snapshot_id: string;
}

const FEEDBACK_ACTIONS = ["ACCEPT", "COMPLETE", "MODIFY", "IGNORE", "REJECT"] as const;

export function RecommendationsWorkspace() {
  const { advisorId, refreshNonce } = useScopedAdvisor();
  const [data, setData] = useState<GenerateResponse | null>(null);
  const [impact, setImpact] = useState<ImpactTrend | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastEffect, setLastEffect] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    apiClient
      .get<ImpactTrend>("/feedback-learning/impact-trend")
      .then(setImpact)
      .catch(() => setImpact(null));
  }, []);

  const submitFeedback = async (rec: Recommendation, action: string) => {
    setBusy(true);
    try {
      const result = await apiClient.post<{ effect: string }>("/feedback-learning/submit", {
        recommendation_id: rec.recommendation_id,
        action,
        action_family: rec.action_family,
      });
      setLastEffect(result.effect);
      await generate(); // re-rank immediately so the learning effect is visible
    } catch (err) {
      setError(err instanceof Error ? err.message : "Feedback failed");
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
          const t = impact?.totals;
          const total = t ? t.accepted + t.implemented + t.rejected + (t as { modified?: number }).modified! + (t as { ignored?: number }).ignored! : 0;
          const pct = (n: number) => (total ? `${Math.round((n / total) * 100)}%` : "—");
          const cards = [
            { label: "Accepted", n: t?.accepted ?? 0, color: colors.positive, bg: "#F0FDFA", icon: CheckCircle2 },
            { label: "Completed", n: t?.implemented ?? 0, color: "#059669", bg: "#ECFDF5", icon: CircleCheck },
            { label: "In Progress", n: (t as { modified?: number } | undefined)?.modified ?? 0, color: colors.warning, bg: "#FFFBEB", icon: PencilLine },
            { label: "Rejected", n: t?.rejected ?? 0, color: colors.negative, bg: "#FEF2F2", icon: XCircle },
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
          <div className="mt-2 h-[240px] animate-pulse rounded-lg bg-slate-100" />
        )}
      </div>

      {lastEffect ? (
        <div
          className="rounded-lg border px-3 py-2 text-[12px]"
          style={{ borderColor: "#C7D2FE", backgroundColor: "#EEF2FF", color: colors.aiAccent }}
        >
          Learning signal applied: {lastEffect}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">{error}</div>
      ) : null}

      <div className="space-y-3">
        {recs.map((rec, index) => (
          <AiContentCard
            key={rec.recommendation_id}
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
                <div className="flex gap-1.5">
                  {FEEDBACK_ACTIONS.map((action) => {
                    const m = ACTION_META[action];
                    const Icon = m.icon;
                    return (
                      <button
                        key={action}
                        onClick={() => void submitFeedback(rec, action)}
                        disabled={busy}
                        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold uppercase tracking-wide disabled:opacity-50"
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
                <div className="mb-1.5 flex items-center gap-1.5">
                  {(() => { const m = familyMeta(rec.action_family); const Icon = m.icon; return (
                    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.04em]" style={{ color: m.color, backgroundColor: `${m.color}14` }}>
                      <Icon style={{ width: 12, height: 12 }} /> {m.label}
                    </span>
                  ); })()}
                </div>
                <p className={type.body} style={{ color: colors.text.primary }}>{rec.action_text}</p>
                <p className={`mt-1 ${type.data}`} style={{ color: colors.text.muted }}>
                  priority {rec.priority_score} = base {rec.base_priority_score} × learned weight {rec.learning_weight}
                  {" · "}confidence {(rec.confidence * 100).toFixed(0)}%
                  {" · "}est. impact ${Math.round(rec.estimated_revenue_impact).toLocaleString()}
                </p>
              </div>
              <SeverityBadge value={rec.severity} />
            </div>
          </AiContentCard>
        ))}
        {recs.length === 0 && !busy ? (
          <p className={type.body} style={{ color: colors.text.muted }}>
            No open recommendations for this advisor.
          </p>
        ) : null}
      </div>

      {/* RL feedback-loop showcase — how weights move with feedback over rounds (9.5, Fable-designed) */}
      <LearningStateShowcase />

      <OutcomeLearningPanel />
    </div>
  );
}
