"use client";

import { colors } from "@/styles/tokens";
import type { CrmPipelineStage } from "@/lib/api/crm";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

// Canonical OPEN pipeline stages in progression order. Terminal WON/LOST are shown
// separately as outcomes, not funnel bands (a funnel encodes forward progression).
const OPEN_STAGES = ["PROSPECT", "QUALIFY", "PROPOSE", "NEGOTIATE"];
// Sequential blue ramp (dark → light) down the funnel — standard funnel styling.
const BAND_FILL = ["#1D4ED8", "#2563EB", "#3B82F6", "#60A5FA"];

const VB_W = 360;
const BAND_H = 52;
const GAP = 8;
const W_MAX = 300; // widest band (px in viewBox)
const W_MIN = 96; // floor so an empty stage still reads as a band

/**
 * CRM pipeline funnel (CLAUDE.md 12.5) — a polished, standard tapering funnel.
 * Each open stage is a centered trapezoid whose top edge meets the previous band
 * and whose width ∝ opportunity count (with a floor so sparse per-advisor data
 * still reads as a funnel). Stage-to-stage conversion % is labelled on the right;
 * each band carries its real count + $ pipeline amount. Terminal Won/Lost are
 * surfaced beneath as outcome chips (not funnel bands). Rendered as SVG so the
 * silhouette is crisp and never collapses to a blank measure race.
 */
export function CrmStageFunnel({ data }: { data: CrmPipelineStage[] }) {
  const byStage = Object.fromEntries(data.map((d) => [d.stage.toUpperCase(), d]));
  const stages = OPEN_STAGES.map((s) => ({
    stage: s,
    label: s.charAt(0) + s.slice(1).toLowerCase(),
    count: byStage[s]?.opportunity_count ?? 0,
    amount: byStage[s]?.pipeline_amount ?? 0,
  }));
  const maxCount = Math.max(1, ...stages.map((s) => s.count));
  // Band width for each stage (top edge = own width; bottom edge = next stage's width).
  const widths = stages.map((s) => W_MIN + (s.count / maxCount) * (W_MAX - W_MIN));
  const cx = VB_W / 2;
  const vbH = stages.length * (BAND_H + GAP);

  const won = byStage["CLOSED_WON"];
  const lost = byStage["CLOSED_LOST"];

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${VB_W} ${vbH}`} className="h-auto w-full" role="img" aria-label="CRM pipeline funnel">
        {stages.map((s, i) => {
          const topW = widths[i];
          const botW = i < stages.length - 1 ? widths[i + 1] : widths[i] * 0.82;
          const y = i * (BAND_H + GAP);
          const pts = [
            [cx - topW / 2, y],
            [cx + topW / 2, y],
            [cx + botW / 2, y + BAND_H],
            [cx - botW / 2, y + BAND_H],
          ].map((p) => p.join(",")).join(" ");
          const prev = i > 0 ? stages[i - 1].count : null;
          const conv = prev && prev > 0 ? Math.round((s.count / prev) * 100) : null;
          return (
            <g key={s.stage}>
              <polygon points={pts} fill={BAND_FILL[i % BAND_FILL.length]} opacity={s.count === 0 ? 0.4 : 1} />
              <text x={cx} y={y + BAND_H / 2 - 3} textAnchor="middle" fontSize="13" fontWeight={700} fill="#fff">{s.label}</text>
              <text x={cx} y={y + BAND_H / 2 + 13} textAnchor="middle" fontSize="11" fill="#fff" fillOpacity={0.92}>
                {s.count} {s.count === 1 ? "opp" : "opps"} · {compactUsd(s.amount)}
              </text>
              {conv != null && (
                <text x={VB_W - 4} y={y + 2} textAnchor="end" fontSize="10" fill={colors.text.muted}>
                  {conv}% →
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <div className="flex items-center justify-center gap-2">
        <span className="rounded-full px-2.5 py-1 text-[11px] font-semibold" style={{ color: "#0F766E", backgroundColor: "#F0FDFA" }}>
          Won {won?.opportunity_count ?? 0} · {compactUsd(won?.pipeline_amount ?? 0)}
        </span>
        <span className="rounded-full px-2.5 py-1 text-[11px] font-semibold" style={{ color: "#B91C1C", backgroundColor: "#FEF2F2" }}>
          Lost {lost?.opportunity_count ?? 0} · {compactUsd(lost?.pipeline_amount ?? 0)}
        </span>
      </div>
      <p className="text-center text-[10px]" style={{ color: colors.text.muted }}>
        Band width ∝ open opportunity count · stage-to-stage conversion % on the right · terminal outcomes shown separately
      </p>
    </div>
  );
}
