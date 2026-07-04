"use client";

import { Funnel, FunnelChart, LabelList, ResponsiveContainer, Tooltip } from "recharts";

import { chartSeries, colors } from "@/styles/tokens";
import type { CrmPipelineStage } from "@/lib/api/crm";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

// canonical stage order so the funnel narrows through the sales process rather
// than by amount (a funnel encodes progression, not ranking).
const ORDER = ["PROSPECT", "QUALIFY", "PROPOSE", "NEGOTIATE", "CLOSED_WON", "CLOSED_LOST"];

/** CRM pipeline by stage -> funnel (dataviz rule for pipeline stages). Each band
 * is the real summed opportunity amount at that stage. */
export function CrmPipelineFunnel({ data }: { data: CrmPipelineStage[] }) {
  const rows = [...data]
    .sort((a, b) => {
      const ia = ORDER.indexOf(a.stage);
      const ib = ORDER.indexOf(b.stage);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    })
    .map((s, i) => ({
      name: `${s.stage.replace("_", " ")} · ${s.opportunity_count}`,
      value: s.pipeline_amount,
      fill: chartSeries[i % chartSeries.length],
    }));

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <FunnelChart>
          <Tooltip
            contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
            formatter={(v: number) => [compactUsd(v), "Pipeline"]}
          />
          <Funnel dataKey="value" data={rows} isAnimationActive>
            <LabelList position="right" dataKey="name" style={{ fontSize: 11, fill: colors.text.secondary }} />
            <LabelList position="left" dataKey="value" formatter={(v: number) => compactUsd(v)} style={{ fontSize: 10, fill: colors.text.muted }} />
          </Funnel>
        </FunnelChart>
      </ResponsiveContainer>
    </div>
  );
}
