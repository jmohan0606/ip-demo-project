import { colors, type } from "@/styles/tokens";

export function KpiStatCard({
  label,
  value,
  delta,
  deltaPositive,
}: {
  label: string;
  value: string;
  delta?: string;
  deltaPositive?: boolean;
}) {
  return (
    <div className="rounded-xl border bg-white px-4 py-3 shadow-sm" style={{ borderColor: colors.surface.border }}>
      <div className={type.label} style={{ color: colors.text.muted }}>{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className={type.kpiValue} style={{ color: colors.text.primary }}>{value}</span>
        {delta ? (
          <span
            className="rounded-full px-1.5 py-0.5 text-[11px] font-semibold"
            style={{
              color: deltaPositive ? colors.positive : colors.negative,
              backgroundColor: deltaPositive ? "#F0FDFA" : "#FEF2F2",
            }}
          >
            {delta}
          </span>
        ) : null}
      </div>
    </div>
  );
}
