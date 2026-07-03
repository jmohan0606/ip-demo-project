"use client";

import { useCallback, useEffect, useState } from "react";

import { AiContentCard } from "@/components/patterns/ai-content-card";
import { EvidenceTracePills } from "@/components/patterns/evidence-trace";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { SeverityBadge } from "@/components/patterns/severity-badge";
import { apiClient } from "@/lib/api/client";
import { colors, type } from "@/styles/tokens";

interface Contribution {
  feature: string;
  value: number | string | null;
  points: number;
  why: string;
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
  enrolled?: boolean;
}

export function PredictionWorkspace({ advisorId = "A001" }: { advisorId?: string }) {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [busy, setBusy] = useState(false);

  const run = useCallback(async () => {
    setBusy(true);
    try {
      const data = await apiClient.post<{ predictions: Prediction[] }>(`/predictions/run/${advisorId}`);
      setPredictions(data.predictions.filter((p) => p.enrolled !== false));
    } finally {
      setBusy(false);
    }
  }, [advisorId]);

  useEffect(() => {
    void run();
  }, [run]);

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>Prediction &amp; Forecasting</h1>
          <p className={type.body} style={{ color: colors.text.secondary }}>
            Transparent scoring for advisor {advisorId} — every point of every score is attributed to a
            named feature and persisted with a reasoning trace.
          </p>
        </div>
        <button
          onClick={() => void run()}
          disabled={busy}
          className="rounded-lg px-3 py-1.5 text-[13px] font-semibold text-white disabled:opacity-50"
          style={{ backgroundColor: colors.primary }}
        >
          {busy ? "Scoring…" : "Re-run predictions"}
        </button>
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
          </AiContentCard>
        ))}
        {predictions.length === 0 && !busy ? (
          <p className={type.body} style={{ color: colors.text.muted }}>No active predictions.</p>
        ) : null}
      </div>
    </div>
  );
}
