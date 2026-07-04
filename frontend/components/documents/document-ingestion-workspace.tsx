"use client";

import { useEffect, useState } from "react";

import { DocumentUpload } from "@/components/knowledge/document-upload";
import { listKnowledgeDocuments, type CatalogDocument } from "@/lib/api/knowledge";
import { colors, type } from "@/styles/tokens";

export function DocumentIngestionWorkspace() {
  const [docs, setDocs] = useState<CatalogDocument[]>([]);

  async function refresh() {
    try {
      setDocs(await listKnowledgeDocuments());
    } catch {
      /* best-effort catalog */
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div>
        <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>Document Ingestion</h1>
        <p className={type.body} style={{ color: colors.text.secondary }}>
          Upload firm documents through the real pipeline — parse, chunk, embed (sentence-transformers)
          and index to Chroma. Ingested documents become retrievable in the Knowledge Hub and cited in
          RAG answers, coaching cards and recommendation explainability.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <DocumentUpload onUploaded={() => void refresh()} />
        <div className="rounded-xl border bg-white shadow-sm" style={{ borderColor: colors.surface.border }}>
          <div className="flex items-center justify-between border-b px-4 py-2.5" style={{ borderColor: colors.surface.border }}>
            <h3 className={type.cardTitle} style={{ color: colors.text.primary }}>Indexed corpus</h3>
            <span className={type.data} style={{ color: colors.text.muted }}>{docs.length} documents</span>
          </div>
          <div className="max-h-[420px] overflow-auto">
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
      </div>
    </div>
  );
}
