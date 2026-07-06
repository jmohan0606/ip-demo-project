"use client";

import { useCallback, useEffect, useState } from "react";

import { Brain, Clock } from "lucide-react";

import { EvidenceTracePills } from "@/components/patterns/evidence-trace";
import { ContextPipelinePanel } from "@/components/explainability/context-pipeline-panel";
import { PipelineTraceBar } from "@/components/explainability/pipeline-trace-bar";
import { SeverityBadge } from "@/components/patterns/severity-badge";
import { AdvisorSelector } from "@/components/status/advisor-selector";
import { apiClient } from "@/lib/api/client";
import { useScopedAdvisor } from "@/lib/hooks/use-scoped-advisor";
import { colors, type } from "@/styles/tokens";

interface Vertex {
  v_id: string;
  v_type: string;
  attributes: Record<string, unknown>;
}

interface MemoryItem {
  memory_id: string;
  memory_type: string;
  title: string | null;
  summary: string | null;
  confidence: number | null;
  source: string | null;
  valid_from: string | null;
  created_ts: string | null;
}

const MEMORY_TYPE_COLOR: Record<string, string> = {
  "Conversation Memory": "#2563EB",
  "Semantic Memory": "#14B8A6",
  "Coaching Memory": "#4F46E5",
  "Episodic Memory": "#F59E0B",
};

// A legible one-line summary per lineage stage (client-readable, not raw ids).
function stageSummary(key: string, items: Vertex[]): string {
  if (!items.length) return "—";
  const a = items[0].attributes;
  switch (key) {
    case "features": return `${items[0].v_id} · versioned snapshot`;
    case "predictions": return `${String(a.prediction_type ?? "prediction").replace(/_/g, " ")} · ${a.score ?? "?"}/100`;
    case "opportunities": return `${String(a.category ?? a.opportunity_type ?? "opportunity")} · sev ${a.severity ?? "?"}`;
    case "recommendation": return String(a.title ?? items[0].v_id);
    case "feedback": return `${String(a.action ?? "feedback")}`;
    case "outcomes": return `${String(a.outcome_type ?? "outcome")}${a.outcome_value ? ` · $${Number(a.outcome_value).toLocaleString()}` : ""}`;
    case "learning": return `${String(a.signal_type ?? "signal")} · reward ${a.reward ?? "?"}`;
    default: return items.map((v) => v.v_id).join(", ").slice(0, 34);
  }
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
  const [memories, setMemories] = useState<MemoryItem[]>([]);
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
    // Real memory-timeline content for this advisor (CLAUDE.md 9.5).
    apiClient
      .post<MemoryItem[] | { memories: MemoryItem[] }>("/memory/retrieve", { scope_type: "Advisor", scope_id: advisorId, limit: 12 })
      .then((res) => setMemories(Array.isArray(res) ? res : res.memories ?? []))
      .catch(() => setMemories([]));
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
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>Explainability Explorer</h1>
          <p className={type.body} style={{ color: colors.text.secondary }}>
            Full artifact chain for advisor {advisorId}: every AI output traces back to the features,
            reasoning steps and evidence that produced it — and forward to feedback and learning.
          </p>
        </div>
        <AdvisorSelector />
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

      {/* Section 13B.1: the "How It Works" pipeline trace (narrative/timing view) above
          the artifact-graph lineage chain — same selected recommendation. */}
      {selectedRec && <PipelineTraceBar recommendationId={selectedRec} />}

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
                  <div className="mt-0.5 max-w-[150px] text-[10px]" style={{ color: colors.text.secondary }}>
                    {stageSummary(stage.key, items)}
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
          <div className="mt-3 space-y-1">
            {evidence && typeof evidence === "object" ? (
              Object.entries(evidence).map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between gap-3 rounded-md border px-2 py-1" style={{ borderColor: colors.surface.border }}>
                  <span className={type.data} style={{ color: colors.text.secondary }}>{k.replace(/_/g, " ")}</span>
                  <span className={`font-mono ${type.data} text-right`} style={{ color: colors.text.primary }}>
                    {typeof v === "object" ? JSON.stringify(v) : String(v)}
                  </span>
                </div>
              ))
            ) : (
              <p className={type.data} style={{ color: colors.text.muted }}>Select a recommendation to see its evidence.</p>
            )}
          </div>
        </div>
      </div>

      {/* Context Engineering Pipeline — visible retrieve→rerank→prune trace (Section 11.6) */}
      <ContextPipelinePanel />

      {/* Memory Timeline — real temporal-memory content for this advisor (CLAUDE.md 9.5) */}
      <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4" style={{ color: colors.aiAccent }} />
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Memory Timeline</h2>
          <span className="text-[11px]" style={{ color: colors.text.muted }}>· temporal context the system remembers about {advisorId}</span>
        </div>
        <p className="mt-1.5 rounded-lg border px-3 py-1.5 text-[11px]" style={{ borderColor: "#C7D2FE", background: "#EEF2FF", color: "#3730A3" }}>
          Part of the temporal knowledge graph (Section 11.4): this timeline is the episodic/conversation
          record over time, alongside point-in-time <a href="/features-embeddings" className="underline">feature snapshots</a> and
          the <a href="/graph-explorer" className="underline">as-of graph traversal</a> — the same entity&apos;s
          state and relationships as they were on any chosen date.
        </p>
        {memories.length === 0 ? (
          <p className={`mt-2 ${type.data}`} style={{ color: colors.text.muted }}>
            No memories recorded yet. Ask the AI Assistant about this advisor, or run a coaching insight, to write to memory.
          </p>
        ) : (
          <ol className="relative mt-3 space-y-3 border-l pl-4" style={{ borderColor: colors.surface.border }}>
            {memories.map((m) => {
              const tint = MEMORY_TYPE_COLOR[m.memory_type ?? ""] ?? colors.text.muted;
              return (
                <li key={m.memory_id} className="relative">
                  <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full ring-2 ring-white" style={{ backgroundColor: tint }} />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.04em]" style={{ color: tint, backgroundColor: `${tint}14` }}>
                      {m.memory_type}
                    </span>
                    <span className="flex items-center gap-1 text-[10px]" style={{ color: colors.text.muted }}>
                      <Clock className="h-3 w-3" /> {m.valid_from ?? m.created_ts ?? "—"}
                    </span>
                    {m.confidence != null && <span className="text-[10px]" style={{ color: colors.text.muted }}>conf {(m.confidence * 100).toFixed(0)}%</span>}
                    {m.source && <span className="text-[10px]" style={{ color: colors.text.muted }}>· {m.source}</span>}
                  </div>
                  {m.title && <div className={`mt-0.5 ${type.data} font-semibold`} style={{ color: colors.text.primary }}>{m.title}</div>}
                  {m.summary && <p className={`mt-0.5 ${type.data} whitespace-pre-wrap`} style={{ color: colors.text.secondary }}>{m.summary.length > 260 ? `${m.summary.slice(0, 260)}…` : m.summary}</p>}
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </div>
  );
}
