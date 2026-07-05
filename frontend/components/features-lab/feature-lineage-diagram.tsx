"use client";

import { ArrowRight, Database, FunctionSquare, Layers, Cpu } from "lucide-react";

import { colors, type } from "@/styles/tokens";

interface LineageEntry {
  group: string;
  source: string;
  evidence: Record<string, unknown>;
}

/**
 * Visual source → feature flow diagram (CLAUDE.md 9.5: "make the lineage section
 * visual — a real diagram of source→feature flow, not a text list"). Renders the
 * real pipeline stages for a selected feature as connected nodes:
 *   Graph evidence facts → Source query (GQ-###) → Feature (group + value) → downstream consumers.
 * Every node is backed by the real snapshot lineage; downstream consumers reflect the
 * actual pipeline (features feed predictions/opportunities/recommendations).
 */
function Stage({ icon: Icon, label, tint, children }: { icon: typeof Database; label: string; tint: string; children: React.ReactNode }) {
  return (
    <div className="flex min-w-[150px] max-w-[220px] flex-1 flex-col rounded-xl border p-3" style={{ borderColor: tint, backgroundColor: `${tint}0d` }}>
      <div className="mb-1.5 flex items-center gap-1.5">
        <Icon className="h-3.5 w-3.5" style={{ color: tint }} />
        <span className={type.label} style={{ color: tint }}>{label}</span>
      </div>
      {children}
    </div>
  );
}

function Arrow() {
  return (
    <div className="flex shrink-0 items-center self-center" style={{ color: colors.text.muted }}>
      <ArrowRight className="h-5 w-5" />
    </div>
  );
}

export function FeatureLineageDiagram({ name, value, entry }: { name: string; value: number | string | null; entry: LineageEntry }) {
  const facts = Object.entries(entry.evidence || {});
  const fmtVal = (v: unknown) => {
    if (Array.isArray(v)) return v.join(" → ");
    if (typeof v === "number") return v.toLocaleString();
    return String(v);
  };
  return (
    <div className="flex flex-wrap items-stretch gap-2 overflow-x-auto">
      <Stage icon={Database} label="Graph Evidence" tint={colors.text.secondary}>
        {facts.length ? (
          <ul className="space-y-1">
            {facts.slice(0, 6).map(([k, v]) => (
              <li key={k} className="rounded border px-1.5 py-0.5 text-[10px]" style={{ borderColor: colors.surface.border, color: colors.text.secondary }}>
                <span className="font-semibold">{k}</span>: <span className="font-mono">{fmtVal(v)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <span className={type.data} style={{ color: colors.text.muted }}>Derived / no raw facts</span>
        )}
      </Stage>

      <Arrow />

      <Stage icon={FunctionSquare} label="Source Query" tint={colors.primary}>
        <span className={`font-mono ${type.data}`} style={{ color: colors.text.primary }}>{entry.source}</span>
        <span className="mt-1 text-[10px]" style={{ color: colors.text.muted }}>graph query / computation</span>
      </Stage>

      <Arrow />

      <Stage icon={Layers} label="Feature" tint={colors.positive}>
        <span className={`font-mono ${type.data} font-semibold`} style={{ color: colors.text.primary }}>{name}</span>
        <span className="mt-0.5 rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase" style={{ backgroundColor: `${colors.positive}1a`, color: colors.positive, width: "fit-content" }}>{entry.group}</span>
        <span className="mt-1 font-mono text-[14px] font-black" style={{ color: colors.text.primary }}>{value === null ? "—" : String(value)}</span>
      </Stage>

      <Arrow />

      <Stage icon={Cpu} label="Consumed By" tint={colors.aiAccent}>
        <ul className="space-y-1">
          {["Feature Snapshot (versioned)", "Predictions (contributions)", "Opportunities & Recommendations"].map((c) => (
            <li key={c} className="text-[10px]" style={{ color: colors.text.secondary }}>• {c}</li>
          ))}
        </ul>
      </Stage>
    </div>
  );
}
