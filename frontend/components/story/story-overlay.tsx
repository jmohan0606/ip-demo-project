"use client";

import { ArrowLeft, ArrowRight, X, Play, CheckCircle2, Eye } from "lucide-react";
import { useStoryMode } from "@/components/story/story-mode-provider";

/** Section 13B.2 — the bottom-docked guided overlay. Narrates the real app as it
 * drives through the scenario; the proof chip shows the real value that proves
 * each step (green when it satisfies the check, e.g. "+$52,110.55 = exactly the
 * impact"). Dark-navy surface so page content stays visible above it. */
export function StoryOverlay() {
  const { scenario, step, stepIndex, busy, proof, next, back, exit, runAction } = useStoryMode();
  if (!scenario || !step) return null;
  const n = scenario.steps.length;
  const isLast = stepIndex === n - 1;

  return (
    <div className="fixed inset-x-0 bottom-0 z-[60] border-t px-4 py-3 text-white shadow-2xl"
      style={{ background: "linear-gradient(180deg,#0B1220,#0F172A)", borderColor: "rgba(255,255,255,0.1)" }}>
      <div className="mx-auto flex max-w-6xl items-center gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide" style={{ background: "rgba(37,99,235,0.25)", color: "#93C5FD" }}>{scenario.label}</span>
            <span className="text-[11px] font-semibold text-slate-400">{step.chapter}</span>
            <div className="flex gap-1">
              {scenario.steps.map((_, i) => (
                <span key={i} className="h-1.5 w-1.5 rounded-full" style={{ background: i <= stepIndex ? "#3B82F6" : "rgba(255,255,255,0.2)" }} />
              ))}
            </div>
            <span className="text-[11px] text-slate-500">Step {stepIndex + 1}/{n}</span>
          </div>
          <div className="mt-1 text-[15px] font-bold">{step.title}</div>
          <p className="mt-0.5 line-clamp-2 text-[12px] text-slate-300">{step.narration}</p>
          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="inline-flex items-center gap-1 text-[11px] text-teal-300"><Eye className="h-3 w-3" /> {step.lookAt}</span>
            {proof && (
              <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: proof.pass ? "rgba(20,184,166,0.2)" : "rgba(148,163,184,0.2)", color: proof.pass ? "#5EEAD4" : "#CBD5E1" }}>
                {proof.pass && <CheckCircle2 className="h-3 w-3" />} {proof.label}
              </span>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button onClick={back} disabled={stepIndex === 0 || busy} className="inline-flex h-9 items-center gap-1 rounded-lg px-3 text-[12px] font-semibold text-slate-300 disabled:opacity-40" style={{ border: "1px solid rgba(255,255,255,0.15)" }}>
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </button>
          {step.action ? (
            <button onClick={() => void runAction()} disabled={busy} className="inline-flex h-9 items-center gap-1 rounded-lg bg-teal-500 px-3 text-[12px] font-bold text-white disabled:opacity-50">
              <Play className="h-3.5 w-3.5" /> {busy ? "Working…" : step.action.label}
            </button>
          ) : null}
          {isLast ? (
            <button onClick={exit} className="inline-flex h-9 items-center gap-1 rounded-lg bg-blue-600 px-3 text-[12px] font-bold text-white">Finish</button>
          ) : (
            <button onClick={next} disabled={busy} className="inline-flex h-9 items-center gap-1 rounded-lg bg-blue-600 px-3 text-[12px] font-bold text-white disabled:opacity-50">
              Next <ArrowRight className="h-3.5 w-3.5" />
            </button>
          )}
          <button onClick={exit} title="Exit story mode" className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 hover:text-white" style={{ border: "1px solid rgba(255,255,255,0.15)" }}>
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
