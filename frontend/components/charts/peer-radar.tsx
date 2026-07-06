"use client";

import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { colors } from "@/styles/tokens";
import type { PeerDimension } from "@/lib/api/peers";

/** Multi-metric peer comparison -> radar (dataviz rule). Both series are
 * percentile ranks (0-100) within the real peer group, so the axes are
 * comparable; the advisor's area vs the 50th-percentile peer baseline shows
 * strengths/gaps at a glance. */
export function PeerRadar({ data, advisorName }: { data: PeerDimension[]; advisorName: string }) {
  const rows = data.map((d) => ({
    metric: d.metric,
    advisor: d.advisor_percentile,
    peer: d.peer_median_percentile,
  }));
  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
          <PolarGrid stroke={colors.surface.border} />
          <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: colors.text.secondary }} />
          <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9, fill: colors.text.muted }} angle={90} />
          <Radar isAnimationActive={false} name="Peer median (50th pct)" dataKey="peer" stroke={colors.text.muted} fill={colors.text.muted} fillOpacity={0.12} />
          <Radar isAnimationActive={false} name={advisorName} dataKey="advisor" stroke={colors.primary} fill={colors.primary} fillOpacity={0.32} />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
            formatter={(v: number, n: string) => [`${v.toFixed(0)}th pct`, n]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
