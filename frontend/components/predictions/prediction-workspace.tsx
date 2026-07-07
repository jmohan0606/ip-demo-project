"use client";

import { useCallback, useEffect, useState } from "react";

import { AiContentCard } from "@/components/patterns/ai-content-card";
import { RevenueForecastChart } from "@/components/charts/revenue-forecast-chart";
import { EvidenceTracePills } from "@/components/patterns/evidence-trace";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { SeverityBadge } from "@/components/patterns/severity-badge";
import { ProductSystemLabel } from "@/components/patterns/product-system-label";
import { AdvisorSelector } from "@/components/status/advisor-selector";
import { apiClient } from "@/lib/api/client";
import { useScopedAdvisor } from "@/lib/hooks/use-scoped-advisor";
import { useEntityLabel } from "@/lib/hooks/use-entity-label";
import { colors, type } from "@/styles/tokens";

interface Contribution {
  feature: string;
  value: number | string | null;
  points: number;
  why: string;
}

interface Methodology {
  model_name: string;
  model_family: string;
  model_version: string;
  trained_alternative: string;
  pipeline: string[];
  features_used: string[];
  score_formula: string;
}

interface Prediction {
  prediction_id: string;
  prediction_type: string;
  score: number;
  risk_band: string;
  severity: string;
  confidence: number;
  horizon_days: number;
  contributions: Contribution[];
  feature_snapshot_id: string;
  explanation: string;
  methodology?: Methodology;
  enrolled?: boolean;
}

export function PredictionWorkspace() {
  const { advisorId, refreshNonce } = useScopedAdvisor();
  const { label: entityLabel } = useEntityLabel();
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [busy, setBusy] = useState(false);

  const run = useCallback(async () => {
    if (!advisorId) return;
    setBusy(true);
    try {
      const data = await apiClient.post<{ predictions: Prediction[] }>(`/predictions/run/${advisorId}`);
      setPredictions(data.predictions.filter((p) => p.enrolled !== false));
    } finally {
      setBusy(false);
    }
  }, [advisorId, refreshNonce]);

  useEffect(() => {
    void run();
  }, [run]);

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div className="flex items-center justify-between">
        <div>
          <ProductSystemLabel />
          <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>Prediction &amp; Forecasting</h1>
          <p className={type.body} style={{ color: colors.text.secondary }}>
            Transparent scoring for advisor {entityLabel(advisorId)} — every point of every score is attributed to a
            named feature and persisted with a reasoning trace.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <AdvisorSelector />
          <button
          onClick={() => void run()}
          disabled={busy}
          className="rounded-lg px-3 py-1.5 text-[13px] font-semibold text-white disabled:opacity-50"
          style={{ backgroundColor: colors.primary }}
        >
          {busy ? "Scoring…" : "Re-run predictions"}
        </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiStatCard label="Active predictions" value={String(predictions.length)} />
        <KpiStatCard
          label="Highest risk"
          value={predictions.length ? `${Math.max(...predictions.map((p) => p.score))}/100` : "—"}
        />
        <KpiStatCard
          label="Avg confidence"
          value={
            predictions.length
              ? `${Math.round((predictions.reduce((sum, p) => sum + p.confidence, 0) / predictions.length) * 100)}%`
              : "—"
          }
        />
        <KpiStatCard label="Snapshot" value={predictions[0]?.feature_snapshot_id.slice(0, 14) ?? "—"} />
      </div>

      {advisorId ? <RevenueForecastChart advisorId={advisorId} /> : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {predictions.map((prediction) => (
          <AiContentCard
            key={prediction.prediction_id}
            title={prediction.prediction_type.replaceAll("_", " ")}
            footer={
              <EvidenceTracePills
                items={[
                  { kind: "pred", id: prediction.prediction_id },
                  { kind: "features", id: prediction.feature_snapshot_id },
                  { kind: "trace", id: `REASON_${prediction.prediction_id}` },
                ]}
              />
            }
          >
            <div className="flex items-baseline gap-2">
              <span className={type.kpiValue} style={{ color: colors.text.primary }}>{prediction.score}</span>
              <span className={type.data} style={{ color: colors.text.muted }}>/100 risk</span>
              <SeverityBadge value={prediction.severity} />
            </div>
            <p className={`mt-1 ${type.data}`} style={{ color: colors.text.muted }}>
              confidence {(prediction.confidence * 100).toFixed(0)}% · horizon {prediction.horizon_days} days
            </p>
            <p className={`mt-2 ${type.body}`} style={{ color: colors.text.secondary }}>{prediction.explanation}</p>
            <div className="mt-3 space-y-1">
              <div className={type.label} style={{ color: colors.text.muted }}>Feature contributions</div>
              {prediction.contributions.map((contribution) => {
                const maxPoints = Math.max(...prediction.contributions.map((c) => c.points), 1);
                return (
                  <div key={contribution.feature} className="flex items-center gap-2">
                    <span
                      className={`w-56 truncate font-mono ${type.data}`}
                      style={{ color: colors.text.primary }}
                      title={contribution.why}
                    >
                      {contribution.feature}
                    </span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: "#F1F5F9" }}>
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${(contribution.points / maxPoints) * 100}%`,
                          backgroundColor: contribution.points > 0 ? colors.warning : colors.surface.border,
                        }}
                      />
                    </div>
                    <span className={`w-12 text-right font-mono ${type.data}`} style={{ color: colors.text.secondary }}>
                      +{contribution.points}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* How this was derived — pipeline + model + formula (CLAUDE.md 9.5 ML/DL depth) */}
            {prediction.methodology && (
              <div className="mt-3 rounded-lg border p-2.5" style={{ borderColor: colors.surface.border, backgroundColor: colors.surface.canvas }}>
                <div className={type.label} style={{ color: colors.aiAccent }}>How this was derived</div>
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <span className="rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ backgroundColor: "#EEF2FF", color: colors.aiAccent }}>
                    {prediction.methodology.model_name} {prediction.methodology.model_version}
                  </span>
                  <span className={type.data} style={{ color: colors.text.muted }}>{prediction.methodology.model_family}</span>
                </div>
                <ol className="mt-2 space-y-0.5">
                  {prediction.methodology.pipeline.map((step, i) => (
                    <li key={i} className="flex gap-1.5">
                      <span className="font-mono text-[10px]" style={{ color: colors.text.muted }}>{i + 1}.</span>
                      <span className={type.data} style={{ color: colors.text.secondary }}>{step}</span>
                    </li>
                  ))}
                </ol>
                <div className="mt-2 rounded bg-white px-2 py-1 font-mono text-[10px]" style={{ color: colors.text.primary, border: `1px solid ${colors.surface.border}` }}>
                  ƒ {prediction.methodology.score_formula}
                </div>
                <p className="mt-1.5 text-[10px]" style={{ color: colors.text.muted }}>
                  Trained alternative · {prediction.methodology.trained_alternative}
                </p>
              </div>
            )}
          </AiContentCard>
        ))}
        {predictions.length === 0 && !busy ? (
          <p className={type.body} style={{ color: colors.text.muted }}>No active predictions.</p>
        ) : null}
      </div>
    </div>
  );
}
