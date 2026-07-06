"use client";

import { useEffect, useState } from "react";
import { Database, Layers, Brain, Sparkles, ShieldCheck, PackageCheck, Clock } from "lucide-react";

import { apiClient } from "@/lib/api/client";
import { colors, type } from "@/styles/tokens";

interface Stage { key: string; label: string; summary: string; ms: number; artifact: Record<string, unknown> }
interface Trace { recommendation_id: string; advisor_id: string; total_ms: number; timing_basis: string; stages: Stage[] }

const STAGE_ICON: Record<string, typeof Database> = {
  data: Database, features: Layers, model: Brain, derivation: Sparkles, context_compliance: ShieldCheck, output: PackageCheck,
};
const STAGE_COLOR: Record<string, string> = {
  data: "#64748B", features: colors.primary, model: colors.aiAccent, derivation: colors.positive, context_compliance: colors.warning, output: "#059669",
};
const usd = (v: unknown) => (typeof v === "number" ? `$${Math.round(v).toLocaleString()}` : String(v ?? "—"));

/** Section 13B.1 — the "How It Works" SYSTEM TRACE: the 6 real pipeline stages that
 * produced a recommendation, with real artifacts and real per-stage timing. Sits
 * above the artifact-graph lineage chain in the Explainability Explorer. */
export function PipelineTraceBar({ recommendationId }: { recommendationId: string }) {
  const [trace, setTrace] = useState<Trace | null>(null);
  const [openStage, setOpenStage] = useState<string | null>(null);

  useEffect(() => {
    setTrace(null);
    apiClient.get<Trace>(`/explainability/pipeline-trace/${recommendationId}`).then(setTrace).catch(() => setTrace(null));
  }, [recommendationId]);

  if (!trace) return <div className="h-[160px] animate-pulse rounded-xl bg-slate-100" />;
  const maxMs = Math.max(1, ...trace.stages.map((s) => s.ms));

  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm" data-story-target="pipeline-trace" style={{ borderColor: colors.surface.border }}>
      <div className="flex items-center justify-between">
        <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>How It Works · Pipeline Trace</h2>
        <span className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold" style={{ borderColor: colors.surface.border, color: colors.text.muted }}>
          <Clock className="h-3 w-3" /> {trace.timing_basis === "generation" ? "pipeline execution" : "trace assembly"} · {trace.total_ms}ms
        </span>
      </div>
      <p className="mt-0.5 text-[11px]" style={{ color: colors.text.muted }}>
        The real journey that produced this recommendation — every stage shows its actual artifact. Click a stage for detail.
      </p>

      {/* 6 stage cards */}
      <div className="mt-3 grid gap-2 md:grid-cols-6">
        {trace.stages.map((s) => {
          const Icon = STAGE_ICON[s.key] ?? Database;
          const c = STAGE_COLOR[s.key] ?? colors.primary;
          return (
            <button key={s.key} onClick={() => setOpenStage(openStage === s.key ? null : s.key)}
              className="rounded-lg border p-2 text-left transition hover:shadow-sm" style={{ borderColor: openStage === s.key ? c : colors.surface.border, background: openStage === s.key ? `${c}0d` : "white" }}>
              <div className="flex items-center gap-1"><Icon className="h-3.5 w-3.5" style={{ color: c }} /><span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: c }}>{s.label}</span></div>
              <div className="mt-1 text-[11px] leading-tight" style={{ color: colors.text.secondary }}>{s.summary}</div>
              <div className="mt-1 font-mono text-[10px]" style={{ color: colors.text.muted }}>{s.ms}ms</div>
            </button>
          );
        })}
      </div>

      {/* SYSTEM TRACE proportional bar */}
      <div className="mt-3 flex overflow-hidden rounded-lg" style={{ border: `1px solid ${colors.surface.border}` }}>
        {trace.stages.map((s) => {
          const c = STAGE_COLOR[s.key] ?? colors.primary;
          const w = Math.max(6, (s.ms / trace.stages.reduce((a, x) => a + x.ms, 0.0001)) * 100);
          return (
            <div key={s.key} title={`${s.label} ${s.ms}ms`} className="flex items-center justify-center py-1.5 text-[9px] font-bold text-white" style={{ width: `${w}%`, background: c, minWidth: 0 }}>
              <span className="truncate px-1">{w > 12 ? `${s.label} ${s.ms}ms` : ""}</span>
            </div>
          );
        })}
      </div>

      {/* Stage detail drawer */}
      {openStage && (() => {
        const s = trace.stages.find((x) => x.key === openStage)!;
        const a = s.artifact as Record<string, unknown>;
        return (
          <div className="mt-3 rounded-lg border p-3 text-[12px]" style={{ borderColor: colors.surface.border, background: colors.surface.canvas }}>
            <div className="mb-1.5 text-[10px] font-bold uppercase tracking-wide" style={{ color: STAGE_COLOR[s.key] }}>{s.label} — real artifact</div>
            {s.key === "features" && Array.isArray(a.top_features) ? (
              <div className="grid gap-1 sm:grid-cols-2">
                {(a.top_features as Array<{ name: string; value: unknown }>).map((f) => (
                  <div key={f.name} className="flex justify-between rounded border bg-white px-2 py-1" style={{ borderColor: colors.surface.border }}>
                    <span style={{ color: colors.text.secondary }}>{f.name}</span><span className="font-mono font-semibold">{typeof f.value === "number" && Math.abs(f.value) > 100 ? usd(f.value) : String(f.value)}</span>
                  </div>
                ))}
              </div>
            ) : s.key === "model" && Array.isArray(a.contributions) ? (
              <div className="space-y-1">
                {(a.contributions as Array<{ feature?: string; name?: string; value?: number; contribution?: number }>).map((c, i) => {
                  const v = c.value ?? c.contribution ?? 0;
                  return <div key={i} className="flex items-center gap-2"><span className="w-40 truncate" style={{ color: colors.text.secondary }}>{c.feature ?? c.name}</span><div className="h-1.5 flex-1 rounded-full bg-slate-200"><div className="h-full rounded-full" style={{ width: `${Math.min(100, Math.abs(v) * 4)}%`, background: v >= 0 ? colors.positive : colors.negative }} /></div><span className="w-12 text-right font-mono text-[11px]">{v}</span></div>;
                })}
              </div>
            ) : s.key === "context_compliance" && a.compliance ? (
              <div>
                <span className="rounded-full px-2 py-0.5 text-[11px] font-bold" style={{ color: (a.compliance as { status: string }).status === "PASSED" ? colors.positive : colors.warning, background: (a.compliance as { status: string }).status === "PASSED" ? "#F0FDFA" : "#FFFBEB" }}>{(a.compliance as { status: string }).status}</span>
                <ul className="mt-1.5 list-disc pl-5" style={{ color: colors.text.secondary }}>{((a.compliance as { warnings: string[] }).warnings || []).map((w, i) => <li key={i}>{w}</li>)}</ul>
              </div>
            ) : s.key === "output" && Array.isArray(a.transitions) ? (
              <div className="flex flex-wrap items-center gap-1.5">{(a.transitions as Array<{ to_status: string }>).map((tr, i) => <span key={i} className="rounded-md border px-2 py-0.5 text-[11px]" style={{ borderColor: colors.surface.border }}>{tr.to_status}</span>)}
                {a.status_note ? <span className="mt-1 block w-full text-[11px]" style={{ color: "#065F46" }}>{String(a.status_note)}</span> : null}</div>
            ) : (
              <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px]" style={{ color: colors.text.secondary }}>{JSON.stringify(a, null, 1)}</pre>
            )}
          </div>
        );
      })()}
    </div>
  );
}
