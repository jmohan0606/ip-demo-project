import { colors } from "@/styles/tokens";

/**
 * Page/nav-level product-system label.
 *
 * Section 11.11 (client-corrected): the two AI systems are named at the
 * page/nav level ONLY — the proactive analytics surfaces belong to
 * "iPerform Insights and Coaching"; the reactive Q&A page is
 * "iPerform Coach Q&A Assistant". This is NOT the per-card "✦ AI Generated"
 * chip (that stays literally "AI Generated" — see AiContentCard).
 */
export function ProductSystemLabel({ system = "insights" }: { system?: "insights" | "coach" }) {
  const text = system === "coach" ? "iPerform Coach Q&A Assistant" : "iPerform Insights and Coaching";
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em]"
      style={{ color: colors.aiAccent, backgroundColor: "#EEF2FF", border: "1px solid #C7D2FE" }}
      title="Proactive system: insights, predictions & recommendations delivered automatically"
    >
      {text}
    </span>
  );
}
