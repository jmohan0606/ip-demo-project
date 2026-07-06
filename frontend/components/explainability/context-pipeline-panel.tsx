"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api/client";
import { useShellContext } from "@/components/layout/shell-context";
import { colors, type } from "@/styles/tokens";

interface TraceItem { source: string; title: string; rank_score: number; kept: boolean }
interface Trace {
  resolved_scope: string; scope_aware: boolean; reranker: { mode: string; backend?: string; model?: string };
  retrieved: TraceItem[]; retrieved_count: number; kept: number; pruned: number; top_k: number;
}

const PRESET = "Why is this scope below the peer revenue benchmark and who needs attention?";

export function ContextPipelinePanel() {
  const shell = useShellContext();
  const [q, setQ] = useState(PRESET);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const st = shell.scopeType || "Advisor";
      const sid = shell.scopeId || "A001";
      setTrace(await apiClient.get<Trace>(`/ai-chat/context-trace?question=${encodeURIComponent(q)}&scope_type=${st}&scope_id=${sid}`));
    } finally {
      setBusy(false);
    }
  }, [q, shell.scopeType, shell.scopeId]);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Context Engineering Pipeline</h2>
          <p className={type.data} style={{ color: colors.text.muted }}>
            How context is assembled for an AI answer (Section 11.6): resolved scope → retrieve broadly →
            rerank by relevance → prune to top-{trace?.top_k ?? "K"} → what reaches the prompt.
          </p>
        </div>
      </div>
      <div className="mb-2 flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()}
          className="flex-1 rounded-md border px-2 py-1 text-[12px]" style={{ borderColor: colors.surface.border }} />
        <button onClick={() => void load()} disabled={busy}
          className="rounded-md px-3 py-1 text-[12px] font-semibold text-white disabled:opacity-50" style={{ backgroundColor: colors.primary }}>
          {busy ? "…" : "Trace"}
        </button>
      </div>
      {trace ? (
        <>
          <div className="mb-2 flex flex-wrap gap-2 text-[11px]">
            <span className="rounded-full border px-2 py-0.5" style={{ borderColor: "#C7D2FE", background: "#EEF2FF", color: "#3730A3" }}>
              scope: {trace.resolved_scope}{trace.scope_aware ? " · aggregate rollup" : ""}
            </span>
            <span className="rounded-full border px-2 py-0.5" style={{ borderColor: colors.surface.border, color: colors.text.muted }}>
              reranker: {trace.reranker.mode} ({trace.reranker.backend ?? trace.reranker.model})
            </span>
            <span className="rounded-full border px-2 py-0.5" style={{ borderColor: colors.surface.border, color: colors.text.muted }}>
              retrieved {trace.retrieved_count} → kept {trace.kept} · pruned {trace.pruned}
            </span>
          </div>
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b text-left text-[11px] uppercase" style={{ color: colors.text.muted }}>
                <th className="px-2 py-1">Source</th><th className="px-2 py-1">Item</th>
                <th className="px-2 py-1 text-right">Rank</th><th className="px-2 py-1 text-center">Kept</th>
              </tr>
            </thead>
            <tbody>
              {trace.retrieved.map((r, i) => (
                <tr key={i} className="border-b last:border-0" style={{ borderColor: colors.surface.border, opacity: r.kept ? 1 : 0.5 }}>
                  <td className="px-2 py-1 text-[11px]" style={{ color: colors.text.muted }}>{r.source}</td>
                  <td className="px-2 py-1" style={{ color: colors.text.primary }}>{r.title}</td>
                  <td className="px-2 py-1 text-right font-mono">{r.rank_score.toFixed(3)}</td>
                  <td className="px-2 py-1 text-center">
                    <span style={{ color: r.kept ? colors.positive : colors.text.muted }}>{r.kept ? "✓ in prompt" : "pruned"}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : <p className={type.data} style={{ color: colors.text.muted }}>Loading…</p>}
    </div>
  );
}
