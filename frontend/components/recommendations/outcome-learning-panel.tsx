"use client";

import { useCallback, useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useScopedAdvisor } from "@/lib/hooks/use-scoped-advisor";
import { apiClient } from "@/lib/api/client";
import { colors, type } from "@/styles/tokens";

interface SimilarMatch { entity_id: string; score: number }
interface RankMove { entity_id: string; after_rank: number; before_rank: number | null; move: number | "new" }
interface AffinityRow { family: string; before: number | null; after: number | null; delta: number }
interface BeforeAfter {
  available: boolean;
  hint?: string;
  advisor_id: string;
  similar_before: SimilarMatch[];
  similar_after: SimilarMatch[];
  rank_moves: RankMove[];
  affinity: AffinityRow[];
  separation: { overall_before: number | null; overall_after: number | null; per_family: Record<string, { before: number | null; after: number | null }> };
  link_pred_auc: { before: number | null; after: number | null };
  model_versions: { before: string; after: string };
  events_used: number;
}

function moveBadge(m: RankMove) {
  if (m.move === "new") return { t: "new", fg: colors.aiAccent };
  const v = m.move as number;
  if (v > 0) return { t: `▲${v}`, fg: colors.positive };
  if (v < 0) return { t: `▼${-v}`, fg: colors.negative };
  return { t: "—", fg: colors.text.muted };
}

export function OutcomeLearningPanel() {
  const { advisorId } = useScopedAdvisor();
  const [data, setData] = useState<BeforeAfter | null>(null);
  const [busy, setBusy] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [wall, setWall] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!advisorId) return;
    setBusy(true);
    try {
      setData(await apiClient.get<BeforeAfter>(`/feedback-learning/before-after?advisor_id=${advisorId}&top_k=5`));
    } finally {
      setBusy(false);
    }
  }, [advisorId]);

  useEffect(() => { void load(); }, [load]);

  const runRetrain = useCallback(async () => {
    setRetraining(true);
    const t0 = Date.now();
    try {
      await apiClient.post(`/feedback-learning/retrain`, {});
      setWall((Date.now() - t0) / 1000);
      await load();
    } finally {
      setRetraining(false);
    }
  }, [load]);

  const sepBefore = data?.separation?.overall_before ?? null;
  const sepAfter = data?.separation?.overall_after ?? null;
  const small = sepBefore !== null && sepAfter !== null && Math.abs(sepAfter - sepBefore) < 0.02;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white" style={{ backgroundColor: colors.aiAccent }}>
            iPerform Insights and Coaching
          </span>
          <CardTitle className={type.cardTitle}>Outcome-Driven Learning — the Deeper Layer</CardTitle>
        </div>
        <p className={type.data} style={{ color: colors.text.muted }}>
          Layer 1 (above): feedback moves a family&apos;s ranking weight instantly. Layer 2 (here): recorded
          outcomes periodically reshape the graph&apos;s own sense of which situations are alike — outcome-driven learning.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {!data?.available ? (
          <div className="rounded-lg border p-3 text-[12px]" style={{ borderColor: colors.surface.border, color: colors.text.muted }}>
            {data?.hint ?? "Loading…"}
            <button onClick={() => void runRetrain()} disabled={retraining}
              className="ml-3 rounded-md px-3 py-1 text-[12px] font-semibold text-white disabled:opacity-50" style={{ backgroundColor: colors.aiAccent }}>
              {retraining ? "Retraining…" : "Run Feedback-Driven Retraining"}
            </button>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <button onClick={() => void runRetrain()} disabled={retraining}
                className="rounded-md px-3 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50" style={{ backgroundColor: colors.aiAccent }}>
                {retraining ? "Retraining…" : "Run Feedback-Driven Retraining"}
              </button>
              <span className={type.data} style={{ color: colors.text.muted }}>
                {data.events_used} recorded outcomes · {data.model_versions.before} → {data.model_versions.after}
                {wall !== null ? ` · ${wall.toFixed(1)}s` : ""}
              </span>
            </div>

            {/* metrics */}
            <div className="grid gap-2 text-[12px] sm:grid-cols-3">
              <Metric label="Link-pred AUC" before={data.link_pred_auc.before} after={data.link_pred_auc.after} keep />
              <Metric label="Separation (held-out)" before={sepBefore} after={sepAfter} />
              <div className="rounded-lg border p-2" style={{ borderColor: colors.surface.border }}>
                <div className={type.label} style={{ color: colors.text.muted }}>Per-family separation Δ</div>
                {Object.entries(data.separation.per_family ?? {}).map(([f, v]) => (
                  <div key={f} className="flex justify-between"><span>{f}</span><span className="font-mono">{fmt(v.before)}→{fmt(v.after)}</span></div>
                ))}
              </div>
            </div>

            {small ? (
              <p className="rounded-lg border px-3 py-2 text-[11px]" style={{ borderColor: "#FDE68A", background: "#FFFBEB", color: "#92400E" }}>
                On demo-scale outcome history this shift is small ({fmt(sepBefore)} → {fmt(sepAfter)}) — the
                mechanism is real; the magnitude grows with recorded outcome history.
              </p>
            ) : null}

            {/* before / after similar advisors */}
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-lg border p-3" style={{ borderColor: colors.surface.border }}>
                <div className={type.label} style={{ color: colors.text.secondary }}>Similar advisors — BEFORE</div>
                {data.similar_before.map((m) => (
                  <div key={m.entity_id} className="flex justify-between text-[12px]"><span className="font-mono">{m.entity_id}</span><span>{(m.score * 100).toFixed(1)}%</span></div>
                ))}
              </div>
              <div className="rounded-lg border p-3" style={{ borderColor: colors.aiAccent }}>
                <div className={type.label} style={{ color: colors.text.secondary }}>Similar advisors — AFTER (outcome-driven)</div>
                {data.similar_after.map((m) => {
                  const mv = data.rank_moves.find((r) => r.entity_id === m.entity_id);
                  const b = mv ? moveBadge(mv) : null;
                  return (
                    <div key={m.entity_id} className="flex justify-between text-[12px]">
                      <span className="font-mono">{m.entity_id} {b ? <span style={{ color: b.fg }}>{b.t}</span> : null}</span>
                      <span>{(m.score * 100).toFixed(1)}%</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* per-family affinity */}
            <div>
              <div className={type.label} style={{ color: colors.text.secondary }}>Per-family outcome affinity (before → after)</div>
              <div className="mt-1 space-y-1">
                {data.affinity.map((a) => (
                  <div key={a.family} className="flex items-center gap-2 text-[12px]">
                    <span className="w-40">{a.family}</span>
                    <span className="font-mono">{fmt(a.before)} → {fmt(a.after)}</span>
                    <span className="font-mono font-semibold" style={{ color: a.delta > 0 ? colors.positive : a.delta < 0 ? colors.negative : colors.text.muted }}>
                      ({a.delta > 0 ? "+" : ""}{a.delta})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
        {busy ? <p className={type.data} style={{ color: colors.text.muted }}>Loading…</p> : null}
      </CardContent>
    </Card>
  );
}

function fmt(v: number | null | undefined) {
  return v === null || v === undefined ? "—" : v.toFixed(4);
}

function Metric({ label, before, after, keep }: { label: string; before: number | null; after: number | null; keep?: boolean }) {
  return (
    <div className="rounded-lg border p-2" style={{ borderColor: colors.surface.border }}>
      <div className={type.label} style={{ color: colors.text.muted }}>{label}{keep ? " (retained)" : ""}</div>
      <div className="font-mono text-[13px]">{fmt(before)} → {fmt(after)}</div>
    </div>
  );
}
