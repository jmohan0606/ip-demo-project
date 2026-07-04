"use client";

import { useRef, useState } from "react";

import { uploadKnowledgeDocument, type UploadResult } from "@/lib/api/knowledge";
import { colors, type } from "@/styles/tokens";

const CATEGORIES = [
  "Auto-detect",
  "Compliance",
  "Playbook",
  "AGP Guide",
  "CRM Engagement",
  "Research",
  "Glossary",
  "Practice Guideline",
];

/** Real document ingestion: PDF/DOCX/PPTX/TXT -> parse -> chunk -> embed -> Chroma.
 * Shared by the Knowledge Hub and the Document Ingestion route. */
export function DocumentUpload({ onUploaded }: { onUploaded?: (result: UploadResult) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  async function submit() {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadKnowledgeDocument(file, category === "Auto-detect" ? undefined : category);
      setResult(res);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      onUploaded?.(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border bg-white shadow-sm" style={{ borderColor: colors.surface.border }}>
      <div className="border-b px-4 py-2.5" style={{ borderColor: colors.surface.border }}>
        <h3 className={type.cardTitle} style={{ color: colors.text.primary }}>Add a document</h3>
        <p className={type.data} style={{ color: colors.text.muted }}>
          PDF · DOCX · PPTX · TXT — parsed, chunked, embedded and indexed to Chroma.
        </p>
      </div>
      <div className="space-y-3 px-4 py-3">
        <label
          className="flex cursor-pointer items-center justify-between gap-2 rounded-lg border border-dashed px-3 py-2.5 text-[12px]"
          style={{ borderColor: colors.surface.border, color: colors.text.secondary }}
        >
          <span style={{ color: file ? colors.text.primary : colors.text.muted }}>
            {file ? file.name : "Choose a file…"}
          </span>
          <span className="rounded px-2 py-0.5 text-[11px] font-semibold text-white" style={{ backgroundColor: colors.text.secondary }}>
            Browse
          </span>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.pptx,.txt,.md"
            className="hidden"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setResult(null);
              setError(null);
            }}
          />
        </label>

        <div className="flex items-center gap-2">
          <span className={type.label} style={{ color: colors.text.muted }}>Category</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="flex-1 rounded-lg border px-2 py-1.5 text-[12px]"
            style={{ borderColor: colors.surface.border, color: colors.text.primary }}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <button
          onClick={() => void submit()}
          disabled={!file || busy}
          className="w-full rounded-lg px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-50"
          style={{ backgroundColor: colors.aiAccent }}
        >
          {busy ? "Ingesting…" : "Ingest to knowledge base"}
        </button>

        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">{error}</div>
        ) : null}

        {result ? (
          <div
            className="rounded-lg border px-3 py-2 text-[12px]"
            style={{ borderColor: colors.positive, backgroundColor: "#F0FDFA", color: colors.text.primary }}
          >
            <div className="font-semibold" style={{ color: colors.positive }}>Indexed ✓</div>
            <div className={`mt-1 ${type.data}`} style={{ color: colors.text.secondary }}>
              <strong>{result.document_name}</strong> — {result.chunks_created} chunk
              {result.chunks_created === 1 ? "" : "s"} · category{" "}
              <strong>{result.document_category}</strong> · {result.document_id}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
