"use client";

import { useEffect, useState } from "react";

import { AiContentCard } from "@/components/patterns/ai-content-card";
import { DocumentUpload } from "@/components/knowledge/document-upload";
import {
  askKnowledge,
  listKnowledgeDocuments,
  type CatalogDocument,
  type RagAnswer,
} from "@/lib/api/knowledge";
import { colors, type } from "@/styles/tokens";

const SUGGESTIONS = [
  "What dollar threshold requires supervisory principal review before presenting a recommendation?",
  "How do I get more referrals from my existing clients?",
  "When does an advisor's AGP milestone attainment trigger a recovery plan?",
  "What is the standard for handling overdue follow-ups in the pipeline?",
];

function similarityColor(sim: number | null): string {
  if (sim === null) return colors.text.muted;
  if (sim >= 0.6) return colors.positive;
  if (sim >= 0.45) return colors.primary;
  if (sim >= 0.3) return colors.warning;
  return colors.text.muted;
}

export function KnowledgeWorkspace() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<RagAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [docs, setDocs] = useState<CatalogDocument[]>([]);

  async function refreshDocs() {
    try {
      setDocs(await listKnowledgeDocuments());
    } catch {
      /* catalog is best-effort; the ask/upload paths are the point */
    }
  }

  useEffect(() => {
    void refreshDocs();
  }, []);

  async function ask(text?: string) {
    const q = (text ?? question).trim();
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await askKnowledge(q));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Knowledge query failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div>
        <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>
          Knowledge Hub
        </h1>
        <p className={type.body} style={{ color: colors.text.secondary }}>
          Retrieval-augmented answers over the firm&apos;s playbooks, compliance policy and research.
          Every answer is grounded in semantically-retrieved passages with cited similarity scores —
          no fabricated guidance. Upload new documents to extend the corpus in real time.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Ask column */}
        <div className="space-y-4 lg:col-span-2">
          <div className="rounded-xl border bg-white p-3 shadow-sm" style={{ borderColor: colors.surface.border }}>
            <div className="flex gap-2">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && ask()}
                placeholder="Ask a policy, playbook or research question…"
                className="flex-1 rounded-lg border px-3 py-2 text-[13px] outline-none"
                style={{ borderColor: colors.surface.border, color: colors.text.primary }}
              />
              <button
                onClick={() => ask()}
                disabled={busy}
                className="rounded-lg px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-50"
                style={{ backgroundColor: colors.primary }}
              >
                {busy ? "Retrieving…" : "Ask"}
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => void ask(s)}
                  disabled={busy}
                  className="rounded-full border px-3 py-1 text-[11px] hover:bg-slate-50 disabled:opacity-50"
                  style={{ borderColor: colors.surface.border, color: colors.text.secondary }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
              {error}
            </div>
          ) : null}

          {busy ? (
            <div className="h-40 animate-pulse rounded-xl border bg-slate-100" style={{ borderColor: colors.surface.border }} />
          ) : null}

          {answer && !busy ? <AnswerBlock answer={answer} /> : null}
        </div>

        {/* Upload + catalog column */}
        <div className="space-y-4">
          <DocumentUpload onUploaded={() => void refreshDocs()} />
          <CatalogCard docs={docs} />
        </div>
      </div>
    </div>
  );
}

function AnswerBlock({ answer }: { answer: RagAnswer }) {
  if (!answer.found) {
    return (
      <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
        <div className={type.label} style={{ color: colors.warning }}>No grounded answer</div>
        <p className={`mt-1 ${type.body}`} style={{ color: colors.text.secondary }}>{answer.answer}</p>
        <p className={`mt-2 ${type.data}`} style={{ color: colors.text.muted }}>
          No passage cleared the {answer.retrieval.min_similarity} similarity floor. The assistant
          declined rather than fabricate — try rephrasing or upload a covering document.
        </p>
      </div>
    );
  }

  return (
    <>
      <AiContentCard
        title="Grounded answer"
        footer={
          <span className={type.data} style={{ color: colors.text.muted }}>
            generated by {answer.generated_by.mode}
            {answer.generated_by.model ? ` · ${answer.generated_by.model}` : ""} · grounded in{" "}
            {answer.retrieval.sources_used} passage(s)
          </span>
        }
      >
        <p className={type.body} style={{ color: colors.text.primary, whiteSpace: "pre-wrap" }}>
          {answer.answer}
        </p>
      </AiContentCard>

      <div className="rounded-xl border bg-white shadow-sm" style={{ borderColor: colors.surface.border }}>
        <div className="border-b px-4 py-2.5" style={{ borderColor: colors.surface.border }}>
          <h3 className={type.cardTitle} style={{ color: colors.text.primary }}>
            Cited sources ({answer.sources.length})
          </h3>
        </div>
        <div className="divide-y" style={{ borderColor: colors.surface.border }}>
          {answer.sources.map((s, i) => (
            <div key={s.chunk_id} className="px-4 py-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
                    style={{ backgroundColor: colors.aiAccent }}
                  >
                    {i + 1}
                  </span>
                  <span className={type.data} style={{ color: colors.text.primary, fontWeight: 600 }}>
                    {s.document_name}
                  </span>
                  <span
                    className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                    style={{ backgroundColor: colors.surface.canvas, color: colors.text.secondary }}
                  >
                    {s.document_category}
                  </span>
                </div>
                <SimilarityMeter sim={s.similarity} />
              </div>
              <p className={`mt-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>
                {s.excerpt.length > 320 ? `${s.excerpt.slice(0, 320)}…` : s.excerpt}
              </p>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function SimilarityMeter({ sim }: { sim: number | null }) {
  const pct = sim === null ? 0 : Math.max(0, Math.min(1, sim)) * 100;
  const color = similarityColor(sim);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full" style={{ backgroundColor: "#F1F5F9" }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className={`font-mono ${type.data}`} style={{ color }}>
        {sim === null ? "—" : sim.toFixed(3)}
      </span>
    </div>
  );
}

function CatalogCard({ docs }: { docs: CatalogDocument[] }) {
  return (
    <div className="rounded-xl border bg-white shadow-sm" style={{ borderColor: colors.surface.border }}>
      <div className="flex items-center justify-between border-b px-4 py-2.5" style={{ borderColor: colors.surface.border }}>
        <h3 className={type.cardTitle} style={{ color: colors.text.primary }}>Corpus</h3>
        <span className={type.data} style={{ color: colors.text.muted }}>{docs.length} documents</span>
      </div>
      <div className="max-h-[320px] overflow-auto">
        {docs.length === 0 ? (
          <p className={`px-4 py-3 ${type.data}`} style={{ color: colors.text.muted }}>No documents indexed yet.</p>
        ) : (
          <ul className="divide-y" style={{ borderColor: colors.surface.border }}>
            {docs.map((d) => (
              <li key={d.document_id} className="flex items-center justify-between gap-2 px-4 py-2">
                <span className={type.data} style={{ color: colors.text.primary }}>{d.document_name}</span>
                <span
                  className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                  style={{ backgroundColor: colors.surface.canvas, color: colors.text.secondary }}
                >
                  {d.document_category || d.document_type || "General"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
