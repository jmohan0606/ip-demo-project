import type { ScopeType } from "@/lib/types/navigation";

// A single guided step. The provider executes: setScope → router.push(route) →
// highlight(target) → (on the step's action button) run real API calls → show proof.
export interface StoryStep {
  id: string;
  chapter: string;               // e.g. "1 · Trigger"
  title: string;
  narration: string;             // 2-3 plain-language sentences
  lookAt: string;                // what to look at on the real screen
  route: string;                 // {A} / {D} templated
  scope?: { type: ScopeType; idKey: "advisor" | "division" | "firm" };
  highlight?: string;            // data-story-target value
  action?: {
    label: string;
    calls: Array<{ method: "GET" | "POST"; path: string; body?: Record<string, unknown> }>;
  };
  proof?: {
    path: string;                // {A}/{D} templated
    method?: "GET" | "POST";     // default GET
    check: string;               // key of a checker in the provider's CHECKERS map
  };
}

export interface Scenario {
  id: string;
  label: string;
  persona: string;               // shell persona to set at start
  blurb: string;
  steps: StoryStep[];
}

// ---- Advisor Journey: detect → explain → act → measure → learn --------------
const ADVISOR_STEPS: StoryStep[] = [
  {
    id: "trigger", chapter: "1 · Trigger", title: "A risk is detected",
    narration: "It starts with a real prediction. The revenue-decline model flags this advisor from their own feature snapshot — no one had to go looking.",
    lookAt: "The Revenue Decline Risk score and its confidence — a real model output.",
    route: "/predictions", scope: { type: "Advisor", idKey: "advisor" }, highlight: "prediction-revenue-decline",
    proof: { path: "/predictions/run/{A}", method: "POST", check: "hasPrediction" },
  },
  {
    id: "diagnosis", chapter: "2 · Diagnosis", title: "The AI explains why",
    narration: "The AI Insight Summary explains the risk in plain language, grounded in the advisor's real drivers — revenue, NNM, managed mix, AGP risk.",
    lookAt: "The AI Insight Summary card — Key Drivers and Watch Outs.",
    route: "/advisor-360", scope: { type: "Advisor", idKey: "advisor" }, highlight: "ai-insight-card",
  },
  {
    id: "recommendation", chapter: "3 · Recommendation", title: "A next-best-action is derived",
    narration: "The pipeline turns that risk into a ranked recommendation with a real estimated dollar impact, and its priority = base score × the learned family weight.",
    lookAt: "The top recommendation card — its estimated impact and priority math.",
    route: "/recommendations", scope: { type: "Advisor", idKey: "advisor" }, highlight: "rec-card-top",
    proof: { path: "/recommendations/generate/{A}", method: "POST", check: "captureTopRec" },
  },
  {
    id: "compliance", chapter: "4 · Compliance", title: "Checked before it reaches you",
    narration: "Every recommendation runs through a real compliance check first — blocked-claims, evidence presence, suitability language.",
    lookAt: "The compliance chip on the recommendation card.",
    route: "/recommendations", scope: { type: "Advisor", idKey: "advisor" }, highlight: "rec-compliance-chip",
  },
  {
    id: "action", chapter: "5 · Action", title: "Accept and complete — the real state machine",
    narration: "This button makes real API calls: it accepts, then completes the recommendation through the Section-13 state machine. Watch the card flip to COMPLETED with disabled buttons.",
    lookAt: "The recommendation's status badge and buttons after the action.",
    route: "/recommendations", scope: { type: "Advisor", idKey: "advisor" }, highlight: "rec-card-top",
    action: {
      label: "Accept & Complete (real API)",
      calls: [
        { method: "POST", path: "/feedback-learning/submit", body: { action: "accept" } },
        { method: "POST", path: "/feedback-learning/submit", body: { action: "complete" } },
      ],
    },
  },
  {
    id: "impact", chapter: "6 · Impact", title: "A real consequence is recorded",
    narration: "Completing it generated a real transaction — the recommendation's own estimated impact — recorded in the Impact Ledger and linked back to the rec.",
    lookAt: "The new ledger entry: the transaction id and the recorded impact.",
    route: "/impact-ledger", scope: { type: "Advisor", idKey: "advisor" }, highlight: "ledger-table",
    proof: { path: "/impact-ledger/advisor/{A}", check: "ledgerMatchesImpact" },
  },
  {
    id: "prop-revenue", chapter: "7 · Propagation", title: "Revenue Analytics moved",
    narration: "The same advisor's revenue analytics now reflect the recorded impact — exactly, to the cent. Nothing was regenerated; the transaction simply flows through.",
    lookAt: "The total revenue KPI — compare it to the baseline captured at the start.",
    route: "/revenue-analytics", scope: { type: "Advisor", idKey: "advisor" }, highlight: "revenue-kpi-total",
    proof: { path: "/revenue/analytics?scope_type=ADVISOR&scope_id={A}&period=LTM", check: "revenuePropagated" },
  },
  {
    id: "prop-firm", chapter: "7 · Propagation", title: "The firm rollup moved too",
    narration: "Because the Executive Dashboard aggregates real per-advisor data, the firm-wide revenue rollup moved by exactly the same amount. One action, visible end to end.",
    lookAt: "The firm Revenue KPI on the Executive Dashboard.",
    route: "/dashboard", scope: { type: "Firm", idKey: "firm" }, highlight: "exec-kpi-revenue",
    proof: { path: "/scope/dashboard?scope_type=FIRM&scope_id=F001&period=LTM&compare_to=Prior%20Year", check: "firmPropagated" },
  },
  {
    id: "learning", chapter: "8 · Learning", title: "The system gets smarter",
    narration: "The completed action fed the feedback loop — the family's ranking weight moved up, so similar recommendations will rank higher next time.",
    lookAt: "The Learning State showcase — the weight trajectory.",
    route: "/recommendations", scope: { type: "Advisor", idKey: "advisor" }, highlight: "learning-state",
  },
  {
    id: "closure", chapter: "9 · Closure", title: "Ask the AI about it",
    narration: "Finally, ask the AI Assistant about this advisor — e.g. 'What did this advisor recently complete and what was the impact?'. Because the completed action and its impact are in the assembled context, the answer reflects what just happened (real Claude when the API key is configured).",
    lookAt: "The chat input — ask what this advisor recently completed.",
    route: "/ai-assistant", scope: { type: "Advisor", idKey: "advisor" }, highlight: "chat-input",
  },
  {
    id: "epilogue", chapter: "10 · The cycle continues", title: "It won't re-issue the addressed action",
    narration: "Regenerating recommendations shows the completed opportunity is now Addressed — the system won't surface the same action again. The loop is closed and ready for the next cycle.",
    lookAt: "The Addressed section on the recommendations page.",
    route: "/recommendations", scope: { type: "Advisor", idKey: "advisor" }, highlight: "addressed-section",
    proof: { path: "/recommendations/generate/{A}", method: "POST", check: "opportunityAddressed" },
  },
];

export const SCENARIOS: Scenario[] = [
  {
    id: "advisor-journey", label: "Advisor Journey", persona: "Advisor",
    blurb: "Detect a revenue risk → explain it → act on it → watch the measured impact propagate across every screen → and the system learn. One real advisor, real data, end to end.",
    steps: ADVISOR_STEPS,
  },
];

export const templ = (s: string, ids: { advisor: string; division: string; firm: string }) =>
  s.replace(/\{A\}/g, ids.advisor).replace(/\{D\}/g, ids.division).replace(/\{firm\}/g, ids.firm);
