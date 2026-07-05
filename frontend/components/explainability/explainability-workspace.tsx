"use client";

import { useCallback, useEffect, useState } from "react";

import { EvidenceTracePills } from "@/components/patterns/evidence-trace";
import { SeverityBadge } from "@/components/patterns/severity-badge";
import { apiClient } from "@/lib/api/client";
import { useScopedAdvisor } from "@/lib/hooks/use-scoped-advisor";
import { colors, type } from "@/styles/tokens";

interface Vertex {
  v_id: string;
  v_type: string;
  attributes: Record<string, unknown>;
}

interface ChainResponse {
  recommendation: Vertex[];
  opportunities: Vertex[];
  predictions: Vertex[];
  features: Vertex[];
  playbooks: Vertex[];
  reasoning: Vertex[];
  feedback: Vertex[];
  outcomes: Vertex[];
  learning: Vertex[];
}

const CHAIN_STAGES: Array<{ key: keyof ChainResponse; label: string }> = [
  { key: "features", label: "Feature Snapshot" },
  { key: "predictions", label: "Prediction" },
  { key: "opportunities", label: "Opportunity" },
  { key: "recommendation", label: "Recommendation" },
  { key: "feedback", label: "Feedback" },
  { key: "outcomes", label: "Outcome" },
  { key: "learning", label: "Learning Signal" },
];

export function ExplainabilityWorkspace() {
  const { advisorId, refreshNonce } = useScopedAdvisor();
  const [recIds, setRecIds] = useState<string[]>([]);
  const [selectedRec, setSelectedRec] = useState<string | null>(null);
  const [chain, setChain] = useState<ChainResponse | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!advisorId) return;
    apiClient
      .post<{ recommendations: Array<{ recommendation_id: string }> }>(`/recommendations/generate/${advisorId}`)
      .then((data) => {
        const ids = data.recommendations.map((rec) => rec.recommendation_id);
        setRecIds(ids);
        if (ids[0]) setSelectedRec(ids[0]);
      })
      .catch(() => setRecIds([]));
  }, [advisorId, refreshNonce]);

  const loadChain = useCallback(async (recommendationId: string) => {
    setBusy(true);
    try {
      setChain(await apiClient.get<ChainResponse>(`/explainability/recommendation/${recommendationId}`));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (selectedRec) void loadChain(selectedRec);
  }, [selectedRec, loadChain]);

  const reasoning = chain?.reasoning?.[0];
  const steps: string[] = reasoning
    ? JSON.parse(String(reasoning.attributes.reasoning_steps_json ?? "[]"))
    : [];
  const evidence = reasoning ? JSON.parse(String(reasoning.attributes.evidence_json ?? "{}")) : null;
  const rec = chain?.recommendation?.[0];

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div>
        <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>Explainability Explorer</h1>
        <p className={type.body} style={{ color: colors.text.secondary }}>
          Full artifact chain for advisor {advisorId}: every AI output traces back to the features,
          reasoning steps and evidence that produced it — and forward to feedback and learning.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {recIds.map((id) => (
          <button
            key={id}
            onClick={() => setSelectedRec(id)}
            className="rounded-lg border px-2.5 py-1.5 font-mono text-[11px]"
            style={{
              borderColor: selectedRec === id ? colors.primary : colors.surface.border,
              backgroundColor: selectedRec === id ? "#EFF6FF" : "white",
              color: selectedRec === id ? colors.primary : colors.text.secondary,
            }}
          >
            {id}
          </button>
        ))}
      </div>

      {/* Chain visualization */}
      <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
        <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Lineage chain</h2>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {CHAIN_STAGES.map((stage, index) => {
            const items = (chain?.[stage.key] as Vertex[] | undefined) ?? [];
            return (
              <div key={stage.key} className="flex items-center gap-2">
                {index > 0 ? <span style={{ color: colors.text.muted }}>→</span> : null}
                <div
                  className="rounded-lg border px-3 py-2 text-center"
                  style={{
                    borderColor: items.length ? colors.aiAccent : colors.surface.border,
                    backgroundColor: items.length ? "#EEF2FF" : colors.surface.canvas,
                  }}
                >
                  <div className={type.label} style={{ color: items.length ? colors.aiAccent : colors.text.muted }}>
                    {stage.label}
                  </div>
                  <div className={`mt-0.5 font-mono text-[10px]`} style={{ color: colors.text.secondary }}>
                    {items.length ? items.map((v) => v.v_id).join(", ").slice(0, 34) : "—"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Reasoning steps */}
        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <div className="flex items-center justify-between">
            <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Reasoning steps</h2>
            {rec ? <SeverityBadge value={String(rec.attributes.severity ?? "")} /> : null}
          </div>
          {busy ? <p className={type.data} style={{ color: colors.text.muted }}>Loading…</p> : null}
          <ol className="mt-2 space-y-1.5">
            {steps.map((step, index) => (
              <li key={index} className="flex gap-2">
                <span
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
                  style={{ backgroundColor: colors.aiAccent }}
                >
                  {index + 1}
                </span>
                <span className={type.body} style={{ color: colors.text.primary }}>{step}</span>
              </li>
            ))}
          </ol>
          {rec ? (
            <div className="mt-3 border-t pt-2" style={{ borderColor: colors.surface.border }}>
              <p className={type.data} style={{ color: colors.text.secondary }}>
                confidence {(Number(rec.attributes.confidence ?? 0) * 100).toFixed(0)}% · priority{" "}
                {String(rec.attributes.priority_score)} · {String(rec.attributes.title ?? "")}
              </p>
            </div>
          ) : null}
        </div>

        {/* Evidence */}
        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Evidence</h2>
          <div className="mt-2">
            <EvidenceTracePills
              items={[
                ...(chain?.features ?? []).map((v) => ({ kind: "features", id: v.v_id })),
                ...(chain?.predictions ?? []).map((v) => ({ kind: "pred", id: v.v_id })),
                ...(chain?.playbooks ?? []).map((v) => ({ kind: "playbook", id: v.v_id })),
                ...(chain?.learning ?? []).map((v) => ({ kind: "learning", id: v.v_id })),
              ]}
            />
          </div>
          <pre
            className="mt-3 max-h-72 overflow-auto rounded-lg border p-2 font-mono text-[10px] leading-4"
            style={{ borderColor: colors.surface.border, backgroundColor: colors.surface.canvas, color: colors.text.secondary }}
          >
            {evidence ? JSON.stringify(evidence, null, 2) : "Select a recommendation."}
          </pre>
        </div>
      </div>
    </div>
  );
}
