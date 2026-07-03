/**
 * Canonical design tokens (CLAUDE.md Section 1B). Single source of truth for
 * every color/type/spacing decision — components and Recharts read from here,
 * never inline hex.
 */

export const colors = {
  primary: "#2563EB", // blue — actions, links, primary charts
  positive: "#14B8A6", // teal — favorable deltas
  aiAccent: "#7C3AED", // violet — AI-generated content, agent traces
  warning: "#F59E0B", // amber
  negative: "#DC2626", // red
  surface: {
    sidebar: "#0B1220", // dark navy sidebar (system default)
    sidebarRaised: "#0F172A",
    canvas: "#F8FAFC", // light content canvas
    card: "#FFFFFF",
    border: "#E2E8F0",
  },
  text: {
    primary: "#0F172A",
    secondary: "#475569",
    muted: "#94A3B8",
    onDark: "#E2E8F0",
  },
} as const;

/** Severity palette — maps 1:1 to the spec's Severity_Model (Section 7).
 * info 0-39 · attention 40-69 · urgent 70-84 · critical 85-100 */
export const severity = {
  info: { fg: "#1D4ED8", bg: "#EFF6FF", border: "#BFDBFE", label: "Info" },
  attention: { fg: "#B45309", bg: "#FFFBEB", border: "#FDE68A", label: "Attention" },
  urgent: { fg: "#C2410C", bg: "#FFF7ED", border: "#FED7AA", label: "Urgent" },
  critical: { fg: "#B91C1C", bg: "#FEF2F2", border: "#FECACA", label: "Critical" },
} as const;

export type SeverityLevel = keyof typeof severity;

export function severityFromScore(score: number): SeverityLevel {
  if (score >= 85) return "critical";
  if (score >= 70) return "urgent";
  if (score >= 40) return "attention";
  return "info";
}

export function normalizeSeverity(value: string | null | undefined): SeverityLevel {
  const lowered = (value || "").toLowerCase();
  if (lowered in severity) return lowered as SeverityLevel;
  if (lowered === "high") return "urgent";
  if (lowered === "medium" || lowered === "warn") return "attention";
  return "info";
}

/** Dense enterprise type scale — data-forward, not marketing-site sizing. */
export const type = {
  label: "text-[11px] font-semibold uppercase tracking-[0.08em]",
  body: "text-[13px] leading-5",
  data: "text-[12px] leading-4 tabular-nums",
  kpiValue: "text-[22px] font-bold leading-7 tabular-nums",
  cardTitle: "text-[14px] font-semibold",
  pageTitle: "text-[20px] font-bold",
} as const;

/** Recharts series palette, ordered by assignment priority. */
export const chartSeries = [
  colors.primary,
  colors.positive,
  colors.aiAccent,
  colors.warning,
  "#64748B",
  "#0EA5E9",
] as const;
