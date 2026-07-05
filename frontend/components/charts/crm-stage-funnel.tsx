"use client";

import { colors, chartSeries } from "@/styles/tokens";
import type { CrmPipelineStage } from "@/lib/api/crm";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

// Canonical OPEN pipeline stages in progression order. Terminal WON/LOST are shown
// separately as outcomes, not funnel bands (a funnel encodes forward progression).
const OPEN_STAGES = ["PROSPECT", "QUALIFY", "PROPOSE", "NEGOTIATE"];

/**
 * CRM pipeline funnel — the previous Recharts <Funnel> misrendered because it needs
 * monotonically-descending values and the per-advisor data mixed terminal WON/LOST
 * bands with open stages at non-monotonic amounts. This is a deterministic CSS funnel:
 * the canonical open stages always render in order (zeros included) as centered
 * trapezoid bands whose width ∝ opportunity count, with the stage's real $ amount
 * labelled — so the shape is always a readable funnel regardless of sparse data.
 * Won/Lost are surfaced beneath as outcome chips.
 */
export function CrmStageFunnel({ data }: { data: CrmPipelineStage[] }) {
  const byStage = Object.fromEntries(data.map((d) => [d.stage.toUpperCase(), d]));
  const stages = OPEN_STAGES.map((s) => ({
    stage: s,
    count: byStage[s]?.opportunity_count ?? 0,
    amount: byStage[s]?.pipeline_amount ?? 0,
  }));
  const maxCount = Math.max(1, ...stages.map((s) => s.count));
  const won = byStage["CLOSED_WON"];
  const lost = byStage["CLOSED_LOST"];

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        {stages.map((s, i) => {
          const widthPct = 34 + (s.count / maxCount) * 66; // floor so empty stages still read
          return (
            <div key={s.stage} className="flex flex-col items-center">
              <div
                className="flex items-center justify-between rounded-md px-3 py-1.5 text-white transition-all"
                style={{ width: `${widthPct}%`, backgroundColor: chartSeries[i % chartSeries.length], opacity: s.count === 0 ? 0.45 : 1 }}
              >
                <span className="text-[11px] font-semibold">{s.stage.charAt(0) + s.stage.slice(1).toLowerCase()}</span>
                <span className="text-[11px]">{s.count} · {compactUsd(s.amount)}</span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex items-center justify-center gap-2">
        <span className="rounded-full px-2.5 py-1 text-[11px] font-semibold" style={{ color: "#0F766E", backgroundColor: "#F0FDFA" }}>
          Won {won?.opportunity_count ?? 0} · {compactUsd(won?.pipeline_amount ?? 0)}
        </span>
        <span className="rounded-full px-2.5 py-1 text-[11px] font-semibold" style={{ color: "#B91C1C", backgroundColor: "#FEF2F2" }}>
          Lost {lost?.opportunity_count ?? 0} · {compactUsd(lost?.pipeline_amount ?? 0)}
        </span>
      </div>
      <p className="text-center text-[10px]" style={{ color: colors.text.muted }}>
        Band width ∝ open opportunity count · terminal outcomes shown separately
      </p>
    </div>
  );
}
