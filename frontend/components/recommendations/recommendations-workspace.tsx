"use client";

import { useCallback, useEffect, useState } from "react";

import { AiContentCard } from "@/components/patterns/ai-content-card";
import { EvidenceTracePills } from "@/components/patterns/evidence-trace";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { SeverityBadge } from "@/components/patterns/severity-badge";
import { apiClient } from "@/lib/api/client";
import { colors, type } from "@/styles/tokens";

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

export function RecommendationsWorkspace({ advisorId = "A001" }: { advisorId?: string }) {
  const [data, setData] = useState<GenerateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastEffect, setLastEffect] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setData(await apiClient.post<GenerateResponse>(`/recommendations/generate/${advisorId}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate recommendations");
    } finally {
      setBusy(false);
    }
  }, [advisorId]);

  useEffect(() => {
    void generate();
  }, [generate]);

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
        <button
          onClick={() => void generate()}
          disabled={busy}
          className="rounded-lg px-3 py-1.5 text-[13px] font-semibold text-white disabled:opacity-50"
          style={{ backgroundColor: colors.primary }}
        >
          {busy ? "Working…" : "Regenerate"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiStatCard label="Open recommendations" value={String(recs.length)} />
        <KpiStatCard label="Estimated impact" value={`$${Math.round(totalImpact).toLocaleString()}`} />
        <KpiStatCard label="Feature snapshot" value={data?.feature_snapshot_id?.slice(0, 14) ?? "—"} />
        <KpiStatCard
          label="Learning families"
          value={String(data?.learning_weights.length ?? 0)}
        />
      </div>

      {lastEffect ? (
        <div
          className="rounded-lg border px-3 py-2 text-[12px]"
          style={{ borderColor: "#DDD6FE", backgroundColor: "#F5F3FF", color: colors.aiAccent }}
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
                  {FEEDBACK_ACTIONS.map((action) => (
                    <button
                      key={action}
                      onClick={() => void submitFeedback(rec, action)}
                      disabled={busy}
                      className="rounded-md border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide hover:bg-slate-50 disabled:opacity-50"
                      style={{ borderColor: colors.surface.border, color: colors.text.secondary }}
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </div>
            }
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
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

      <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
        <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Learning state</h2>
        <p className={type.data} style={{ color: colors.text.muted }}>
          Family weights move with every feedback action and re-rank the next generation run.
        </p>
        <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-3">
          {(data?.learning_weights ?? []).map((weight) => (
            <div
              key={weight.family}
              className="flex items-center justify-between rounded-lg border px-3 py-2"
              style={{ borderColor: colors.surface.border }}
            >
              <span className={type.data} style={{ color: colors.text.secondary }}>{weight.family}</span>
              <span
                className="font-mono text-[12px] font-bold"
                style={{ color: weight.weight >= 1 ? colors.positive : colors.negative }}
              >
                {weight.weight.toFixed(2)} ({weight.feedback_count} fb)
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
