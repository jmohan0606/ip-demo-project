import { Award, ListChecks, ShieldCheck, Target } from "lucide-react";

import { AiContentCard } from "@/components/patterns/ai-content-card";
import { colors, type } from "@/styles/tokens";

export interface AiCoachingData {
  tone?: string;
  recommendation: string;
  shoutout: string;
  action_steps: string[];
  guideline_basis: { sources: string[]; note: string };
  talk_track?: string[];
}

/** AI Coaching Card — Recommendation / Shoutout / Action Steps / Guideline Basis
 * (CLAUDE.md 9.5). Structured per-advisor coaching from the insight engine's
 * coaching plan. Reused on Dashboard / Advisor 360 / Client 360. */
export function AiCoachingCard({ data, title = "AI Coaching Card" }: { data: AiCoachingData; title?: string }) {
  return (
    <AiContentCard
      title={title}
      footer={
        <span className={type.data} style={{ color: colors.text.muted }}>
          Guideline basis · {data.guideline_basis.sources.join(" · ")}. {data.guideline_basis.note}
        </span>
      }
    >
      <div className="space-y-3">
        <section className="rounded-lg border p-2.5" style={{ borderColor: colors.surface.border }}>
          <div className="flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5" style={{ color: colors.primary }} />
            <span className={type.label} style={{ color: colors.primary }}>Recommendation</span>
          </div>
          <p className={`mt-1 ${type.body}`} style={{ color: colors.text.primary }}>{data.recommendation}</p>
        </section>

        <section className="rounded-lg border p-2.5" style={{ borderColor: "#CCFBF1", backgroundColor: "#F0FDFA" }}>
          <div className="flex items-center gap-1.5">
            <Award className="h-3.5 w-3.5" style={{ color: colors.positive }} />
            <span className={type.label} style={{ color: colors.positive }}>Shoutout</span>
          </div>
          <p className={`mt-1 ${type.body}`} style={{ color: colors.text.secondary }}>{data.shoutout}</p>
        </section>

        <section>
          <div className="flex items-center gap-1.5">
            <ListChecks className="h-3.5 w-3.5" style={{ color: colors.text.secondary }} />
            <span className={type.label} style={{ color: colors.text.secondary }}>Action Steps</span>
          </div>
          <ol className="mt-1.5 space-y-1">
            {data.action_steps.map((s, i) => (
              <li key={i} className="flex gap-2">
                <span className="flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold" style={{ width: 18, height: 18, backgroundColor: `${colors.primary}14`, color: colors.primary }}>{i + 1}</span>
                <span className={type.data} style={{ color: colors.text.secondary }}>{s}</span>
              </li>
            ))}
          </ol>
        </section>

        {data.guideline_basis.sources.length > 0 && (
          <div className="flex items-center gap-1.5 text-[11px]" style={{ color: colors.text.muted }}>
            <ShieldCheck className="h-3.5 w-3.5" /> Traceable to {data.guideline_basis.sources.length} pipeline sources
          </div>
        )}
      </div>
    </AiContentCard>
  );
}
