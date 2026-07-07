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

// ---- Division-Leader (DDW/MDW) Journey: rollup reasoning → drill → act → propagate ----
// The same real pipeline as the advisor journey, entered at DIVISION scope so a
// division leader sees THEIR journey (Section 13B.3). {A} is pre-resolved by the
// launcher to the division's worst-contributing advisor; {D} is the division.
const DIVISION_STEPS: StoryStep[] = [
  {
    id: "div-trigger", chapter: "1 · Trigger", title: "A division is underperforming",
    narration: "You're a division leader (DDW). The Executive Dashboard, scoped to your division, rolls up every advisor's real data — and it's lagging prior year, with specific advisors dragging the number.",
    lookAt: "The division Revenue KPI and its delta vs prior year — a live rollup, not a hardcoded total.",
    route: "/dashboard", scope: { type: "Division", idKey: "division" }, highlight: "exec-kpi-revenue",
    proof: { path: "/scope/dashboard?scope_type=DIVISION&scope_id={D}&period=LTM&compare_to=Prior%20Year", check: "divisionUnderperformance" },
  },
  {
    id: "div-diagnosis", chapter: "2 · Diagnosis", title: "The AI reasons across your advisors",
    narration: "The AI Insight Summary reasons across ALL advisors in the division — not one resolved advisor — to explain why the division is lagging (Section 11.6 rollup reasoning).",
    lookAt: "The AI Insight Summary — Key Drivers aggregated across the division.",
    route: "/dashboard", scope: { type: "Division", idKey: "division" }, highlight: "ai-insight-card",
    proof: { path: "/scope/ai-insight?scope_type=DIVISION&scope_id={D}&period=LTM&compare_to=Prior%20Year&persona=DDW", check: "divisionInsight" },
  },
  {
    id: "div-contributors", chapter: "3 · Drill in", title: "Which advisors are dragging it",
    narration: "The Bottom Advisors table names the real advisors contributing most to the division's gap, each with a stated reason — this is where a leader looks first.",
    lookAt: "The Bottom Advisors table — real names, real revenue, real reasons.",
    route: "/dashboard", scope: { type: "Division", idKey: "division" }, highlight: "bottom-advisors",
    proof: { path: "/scope/dashboard?scope_type=DIVISION&scope_id={D}&period=LTM&compare_to=Prior%20Year", check: "divisionContributors" },
  },
  {
    id: "div-drill", chapter: "4 · One advisor", title: "Open the top contributor",
    narration: "Drill into that advisor's 360 — the same real book, CRM and AGP data, now viewed as the leader deciding where to intervene.",
    lookAt: "The advisor's AI Insight & Coaching cards — the leader's evidence to act.",
    route: "/advisor-360", scope: { type: "Advisor", idKey: "advisor" }, highlight: "ai-insight-card",
  },
  {
    id: "div-coaching", chapter: "5 · Division action", title: "Assign a coaching task",
    narration: "This button makes a real API call: as the division leader you assign a coaching task to this advisor. It persists to the graph and is retrievable — and becomes context the AI can use.",
    lookAt: "The manager-assigned coaching tasks list for this advisor.",
    route: "/coaching-reviews", scope: { type: "Advisor", idKey: "advisor" }, highlight: "coaching-tasks",
    action: {
      label: "Assign coaching task (real API)",
      calls: [{
        method: "POST", path: "/coaching/tasks",
        body: { advisor_id: "{A}", title: "Division coaching: revenue recovery", category: "PIPELINE",
                instruction: "DDW-assigned: work managed-mix and pipeline opportunities to reverse the division-flagged revenue decline.",
                priority: "HIGH", created_by_user_id: "U_DDW01" },
      }],
    },
    proof: { path: "/coaching/tasks/{A}", check: "coachingTaskAssigned" },
  },
  {
    id: "div-recommendation", chapter: "6 · Recommendation", title: "A next-best-action for the advisor",
    narration: "The same real pipeline generates a ranked recommendation for this advisor, with a real estimated dollar impact and its explainability chain.",
    lookAt: "The top recommendation card — estimated impact and priority.",
    route: "/recommendations", scope: { type: "Advisor", idKey: "advisor" }, highlight: "rec-card-top",
    proof: { path: "/recommendations/generate/{A}", method: "POST", check: "captureTopRec" },
  },
  {
    id: "div-action", chapter: "7 · Act", title: "Accept and complete it",
    narration: "Accept then complete the recommendation through the real Section-13 state machine — recording a real impact transaction for the advisor.",
    lookAt: "The recommendation status flipping to COMPLETED.",
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
    id: "div-impact", chapter: "8 · Division impact", title: "The division rollup moved",
    narration: "Because the division number is a live rollup of its advisors, completing that action moved the DIVISION revenue by exactly the recorded impact. A leader's intervention, visible at their level.",
    lookAt: "The division Revenue KPI — compare to the baseline captured at the start.",
    route: "/dashboard", scope: { type: "Division", idKey: "division" }, highlight: "exec-kpi-revenue",
    proof: { path: "/scope/dashboard?scope_type=DIVISION&scope_id={D}&period=LTM&compare_to=Prior%20Year", check: "divisionPropagated" },
  },
  {
    id: "div-closure", chapter: "9 · Closure", title: "Ask the AI at division scope",
    narration: "Finally, ask the AI Assistant a division-level question. Because the scope is Division, it reasons across your advisors (Section 11.6) and reflects the action just taken — real Claude when the key is configured.",
    lookAt: "The chat input — ask which of your advisors need attention now.",
    route: "/ai-assistant", scope: { type: "Division", idKey: "division" }, highlight: "chat-input",
  },
];

export const SCENARIOS: Scenario[] = [
  {
    id: "advisor-journey", label: "Advisor Journey", persona: "Advisor",
    blurb: "Detect a revenue risk → explain it → act on it → watch the measured impact propagate across every screen → and the system learn. One real advisor, real data, end to end.",
    steps: ADVISOR_STEPS,
  },
  {
    id: "division-journey", label: "Division-Leader Journey", persona: "DDW",
    blurb: "A DDW/MDW view: detect an underperforming division → reason across its advisors → drill into the top contributor → assign a coaching action + complete a recommendation → watch the division rollup move by exactly the impact. Real cross-advisor data, end to end.",
    steps: DIVISION_STEPS,
  },
];

export const templ = (s: string, ids: { advisor: string; division: string; firm: string }) =>
  s.replace(/\{A\}/g, ids.advisor).replace(/\{D\}/g, ids.division).replace(/\{firm\}/g, ids.firm);
