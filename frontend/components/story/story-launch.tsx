"use client";

import { useEffect, useState } from "react";
import { PlayCircle, Sparkles, AlertTriangle } from "lucide-react";

import { useStoryMode } from "@/components/story/story-mode-provider";
import { SCENARIOS } from "@/components/story/scenarios";
import { apiClient } from "@/lib/api/client";
import { colors, type } from "@/styles/tokens";

export function StoryLaunch() {
  const { start, busy, active } = useStoryMode();
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [advisor, setAdvisor] = useState("A005");

  useEffect(() => {
    apiClient.get<{ advisors: Array<{ advisor_id: string; advisor_name: string | null }> }>("/advisor/list")
      .then((r) => setAdvisors(r.advisors.filter((a) => a.advisor_id !== "A001" && a.advisor_id !== "A020")))
      .catch(() => setAdvisors([]));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <div className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-semibold" style={{ borderColor: "#BFDBFE", background: "#EFF6FF", color: colors.primary }}>
          <Sparkles className="h-3.5 w-3.5" /> Guided Story Mode
        </div>
        <h2 className="mt-2 text-[22px] font-black">See the whole system work, end to end</h2>
        <p className="max-w-3xl text-[13px] text-muted-foreground">
          A guided walkthrough that drives the REAL app on REAL data — not a slideshow. It detects a risk with
          a real model, explains it, acts on a recommendation through the real state machine, records a real
          impact, and shows that impact propagate across Revenue Analytics, Advisor 360 and the Executive
          Dashboard — to the cent — then the system learns from it.
        </p>
      </div>

      <div className="rounded-xl border p-3 text-[12px]" style={{ borderColor: "#FDE68A", background: "#FFFBEB", color: "#92400E" }}>
        <div className="flex items-center gap-1.5 font-semibold"><AlertTriangle className="h-4 w-4" /> This performs real actions</div>
        Completing a recommendation really writes a transaction and moves this advisor&apos;s figures (additively,
        recorded in the Impact Ledger). The scenario resets the chosen advisor to a clean baseline before it
        starts, so it&apos;s fully replayable. Anchored verification advisors (A001, A020) are not selectable.
        Learning history (ranking weights) is intentionally cumulative — it is not rewound.
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className={type.label} style={{ color: colors.text.muted }}>Scenario advisor</span>
          <select value={advisor} onChange={(e) => setAdvisor(e.target.value)} className="h-9 rounded-lg border border-border bg-white px-2 text-[13px] font-semibold">
            {(advisors.length ? advisors : [{ advisor_id: "A005", advisor_name: null }]).map((a) => (
              <option key={a.advisor_id} value={a.advisor_id}>{a.advisor_id}{a.advisor_name ? ` — ${a.advisor_name}` : ""}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {SCENARIOS.map((sc) => (
          <div key={sc.id} className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
            <h3 className="text-[15px] font-bold">{sc.label}</h3>
            <p className="mt-1 text-[12px] text-muted-foreground">{sc.blurb}</p>
            <div className="mt-2 text-[11px] text-muted-foreground">{sc.steps.length} steps · persona {sc.persona}</div>
            <button
              onClick={() => void start(sc.id, advisor, "D01")}
              disabled={busy || active}
              className="mt-3 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-[13px] font-bold text-white disabled:opacity-50"
            >
              <PlayCircle className="h-4 w-4" /> {busy ? "Preparing…" : `Start — ${sc.label}`}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
