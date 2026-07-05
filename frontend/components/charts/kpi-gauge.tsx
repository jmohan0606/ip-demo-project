"use client";

import { colors, type } from "@/styles/tokens";

/** Radial attainment gauge (semicircle meter) — a real visual KPI meter
 * (CLAUDE.md 9.12: "real KPI gauges/meters, visual not text"). Fill sweeps 180°
 * proportional to attainment %, colored by on/off-track status. */
export function KpiGauge({
  label,
  pct,
  onTrack,
  size = 108,
}: {
  label: string;
  pct: number;
  onTrack: boolean;
  size?: number;
}) {
  const clamped = Math.max(0, Math.min(100, pct));
  const stroke = 9;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  // Semicircle: 180° from left (180deg) to right (0deg), drawn as an arc path.
  const circumference = Math.PI * r; // half circle
  const dash = (clamped / 100) * circumference;
  const color = onTrack ? colors.positive : colors.negative;

  const arc = (fromDeg: number, toDeg: number) => {
    const p = (deg: number) => {
      const rad = (Math.PI * deg) / 180;
      return [cx + r * Math.cos(rad), cy - r * Math.sin(rad)];
    };
    const [x1, y1] = p(fromDeg);
    const [x2, y2] = p(toDeg);
    return `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`;
  };

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 8} viewBox={`0 0 ${size} ${size / 2 + 8}`}>
        <path d={arc(180, 0)} fill="none" stroke={colors.surface.border} strokeWidth={stroke} strokeLinecap="round" />
        <path
          d={arc(180, 0)}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
        <text x={cx} y={cy - 2} textAnchor="middle" className="font-black" style={{ fontSize: 20, fill: colors.text.primary }}>
          {Math.round(clamped)}%
        </text>
      </svg>
      <div className="mt-0.5 text-center">
        <div className={type.data} style={{ color: colors.text.secondary }}>{label}</div>
        <span
          className="mt-0.5 inline-block rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.05em]"
          style={{ color, backgroundColor: onTrack ? "#F0FDFA" : "#FEF2F2" }}
        >
          {onTrack ? "On Track" : "Off Track"}
        </span>
      </div>
    </div>
  );
}
