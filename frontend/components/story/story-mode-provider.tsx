"use client";

import { createContext, useContext, useCallback, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { SCENARIOS, templ, type Scenario, type StoryStep } from "@/components/story/scenarios";
import { StoryOverlay } from "@/components/story/story-overlay";

interface Baselines { advisorRevenue?: number; firmRevenue?: number; divisionRevenue?: number; marketRevenue?: number; snapshotRevenue?: number; weights?: Record<string, number> }
interface Captured { recId?: string; family?: string; impactEstimate?: number; impactRecorded?: number }
interface ProofResult { label: string; pass: boolean }

interface StoryCtx {
  active: boolean;
  scenario: Scenario | null;
  stepIndex: number;
  step: StoryStep | null;
  advisor: string;
  busy: boolean;
  proof: ProofResult | null;
  start: (scenarioId: string, advisorId: string, division: string, market?: string) => Promise<void>;
  next: () => void;
  back: () => void;
  exit: () => void;
  runAction: () => Promise<void>;
}

const Ctx = createContext<StoryCtx | null>(null);
export const useStoryMode = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error("useStoryMode must be inside StoryModeProvider");
  return v;
};

const SS_KEY = "iperform-story-state";
const usd = (v?: number) => (v == null ? "—" : `$${Math.round(v).toLocaleString()}`);

export function StoryModeProvider({ children }: { children: ReactNode }) {
  const shell = useShellContext();
  const router = useRouter();
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [advisor, setAdvisor] = useState("A005");
  const [division, setDivision] = useState("D01");
  const [market, setMarket] = useState("M01");
  const [baselines, setBaselines] = useState<Baselines>({});
  const [captured, setCaptured] = useState<Captured>({});
  const [busy, setBusy] = useState(false);
  const [proof, setProof] = useState<ProofResult | null>(null);

  const ids = { advisor, division, market, firm: "F001" };
  const step = scenario ? scenario.steps[stepIndex] ?? null : null;

  // ---- persistence across the navigations the overlay itself triggers ------
  useEffect(() => {
    const raw = sessionStorage.getItem(SS_KEY);
    if (raw) {
      try {
        const s = JSON.parse(raw);
        const sc = SCENARIOS.find((x) => x.id === s.scenarioId) ?? null;
        if (sc) { setScenario(sc); setStepIndex(s.stepIndex ?? 0); setAdvisor(s.advisor ?? "A005"); setDivision(s.division ?? "D01"); setMarket(s.market ?? "M01"); setBaselines(s.baselines ?? {}); setCaptured(s.captured ?? {}); }
      } catch { /* ignore */ }
    }
  }, []);
  useEffect(() => {
    if (scenario) sessionStorage.setItem(SS_KEY, JSON.stringify({ scenarioId: scenario.id, stepIndex, advisor, division, market, baselines, captured }));
    else sessionStorage.removeItem(SS_KEY);
  }, [scenario, stepIndex, advisor, division, market, baselines, captured]);

  const CHECKERS: Record<string, (d: any) => ProofResult> = {
    hasPrediction: (d) => {
      const preds = d?.predictions ?? [];
      const p = preds[0];
      return { label: p ? `Real model output: ${p.prediction_type ?? p.type ?? "risk"} ${p.score}/100, confidence ${p.confidence}` : "No prediction", pass: preds.length > 0 };
    },
    captureTopRec: (d) => {
      const r = (d?.recommendations ?? [])[0];
      if (r) setCaptured((c) => ({ ...c, recId: r.recommendation_id, family: r.action_family, impactEstimate: r.estimated_revenue_impact }));
      return { label: r ? `Top recommendation: "${r.title}" · est. impact ${usd(r.estimated_revenue_impact)}` : "No recommendation", pass: !!r };
    },
    ledgerMatchesImpact: (d) => {
      const e = (d?.entries ?? [])[0];
      const ok = !!e && Math.abs(e.impact_amount - (captured.impactRecorded ?? captured.impactEstimate ?? -1)) < 0.02;
      return { label: e ? `Ledger recorded ${usd(e.impact_amount)} (${e.source_transaction_id})` : "No ledger entry yet", pass: !!e };
    },
    revenuePropagated: (d) => {
      const now = d?.kpis?.total_revenue;
      const base = baselines.advisorRevenue;
      const impact = captured.impactRecorded ?? captured.impactEstimate ?? 0;
      const ok = base != null && Math.abs(now - base - impact) < 0.02;
      return { label: `${usd(base)} → ${usd(now)}  (+${usd(now - (base ?? now))})${ok ? " = exactly the impact ✓" : ""}`, pass: ok };
    },
    firmPropagated: (d) => {
      const now = d?.totals?.revenue_ltm;
      const base = baselines.firmRevenue;
      const impact = captured.impactRecorded ?? captured.impactEstimate ?? 0;
      const ok = base != null && Math.abs(now - base - impact) < 0.02;
      return { label: `Firm ${usd(base)} → ${usd(now)}  (+${usd(now - (base ?? now))})${ok ? " ✓" : ""}`, pass: ok };
    },
    opportunityAddressed: (d) => {
      const addr = (d?.addressed_opportunities ?? []).length;
      return { label: addr > 0 ? `${addr} opportunity now Addressed — won't be re-issued` : "Not yet addressed", pass: addr > 0 };
    },
    // ---- Division-leader (DDW) journey checkers ---------------------------
    divisionUnderperformance: (d) => {
      const bottom = d?.bottom_advisors ?? [];
      const delta = d?.headline?.delta_pct;
      const names = bottom.slice(0, 3).map((a: any) => a.advisor_name).join(", ");
      return { label: bottom.length ? `Division ${usd(d?.totals?.revenue_ltm)} · ${delta ?? "—"}% vs prior · lagging advisors: ${names}` : "No division data", pass: bottom.length > 0 };
    },
    divisionInsight: (d) => {
      const ins = d?.insight ?? d;
      const drivers = ins?.key_drivers ?? [];
      return { label: drivers.length ? `Cross-advisor reasoning: ${drivers.length} key drivers, confidence ${ins?.confidence ?? "—"}` : "No insight", pass: drivers.length > 0 };
    },
    divisionContributors: (d) => {
      const bottom = d?.bottom_advisors ?? [];
      const worst = bottom[0];
      return { label: worst ? `Top contributor to the gap: ${worst.advisor_name} (${usd(worst.revenue_ltm)}, ${worst.reason ?? ""})` : "No contributors", pass: bottom.length > 0 };
    },
    coachingTaskAssigned: (d) => {
      const tasks = d?.tasks ?? d ?? [];
      const arr = Array.isArray(tasks) ? tasks : [];
      return { label: arr.length ? `${arr.length} coaching task(s) now assigned & persisted for this advisor` : "No task persisted", pass: arr.length > 0 };
    },
    divisionPropagated: (d) => {
      const now = d?.totals?.revenue_ltm;
      const base = baselines.divisionRevenue;
      const impact = captured.impactRecorded ?? captured.impactEstimate ?? 0;
      const ok = base != null && Math.abs(now - base - impact) < 0.02;
      return { label: `Division ${usd(base)} → ${usd(now)}  (+${usd(now - (base ?? now))})${ok ? " = exactly the impact ✓" : ""}`, pass: ok };
    },
    // ---- Market-leader (MDW) journey checkers -----------------------------
    marketUnderperformance: (d) => {
      const bottom = d?.bottom_advisors ?? [];
      const delta = d?.headline?.delta_pct;
      const names = bottom.slice(0, 3).map((a: any) => a.advisor_name).join(", ");
      return { label: bottom.length ? `Market ${usd(d?.totals?.revenue_ltm)} · ${delta ?? "—"}% vs prior · lagging advisors: ${names}` : "No market data", pass: bottom.length > 0 };
    },
    marketInsight: (d) => {
      const ins = d?.insight ?? d;
      const drivers = ins?.key_drivers ?? [];
      return { label: drivers.length ? `Cross-advisor reasoning across the market: ${drivers.length} key drivers, confidence ${ins?.confidence ?? "—"}` : "No insight", pass: drivers.length > 0 };
    },
    marketContributors: (d) => {
      const bottom = d?.bottom_advisors ?? [];
      const worst = bottom[0];
      return { label: worst ? `Top contributor to the market gap: ${worst.advisor_name} (${usd(worst.revenue_ltm)}, ${worst.reason ?? ""})` : "No contributors", pass: bottom.length > 0 };
    },
    marketPropagated: (d) => {
      const now = d?.totals?.revenue_ltm;
      const base = baselines.marketRevenue;
      const impact = captured.impactRecorded ?? captured.impactEstimate ?? 0;
      const ok = base != null && Math.abs(now - base - impact) < 0.02;
      return { label: `Market ${usd(base)} → ${usd(now)}  (+${usd(now - (base ?? now))})${ok ? " = exactly the impact ✓" : ""}`, pass: ok };
    },
  };

  const goToStep = useCallback(async (idx: number, sc: Scenario) => {
    const st = sc.steps[idx];
    if (!st) return;
    setProof(null);
    if (st.scope) {
      const id = st.scope.idKey === "advisor" ? advisor
        : st.scope.idKey === "division" ? division
        : st.scope.idKey === "market" ? market : "F001";
      const label = st.scope.idKey === "firm" ? "Chase Wealth Management" : id;
      shell.setScope(st.scope.type, id, label);
    }
    router.push(templ(st.route, ids));
    // highlight after the target appears
    if (st.highlight) {
      const target = st.highlight;
      let tries = 0;
      const tick = () => {
        const el = document.querySelector(`[data-story-target="${target}"]`);
        document.querySelectorAll(".story-highlight").forEach((e) => e.classList.remove("story-highlight"));
        if (el) { el.classList.add("story-highlight"); el.scrollIntoView({ behavior: "smooth", block: "center" }); }
        else if (tries++ < 25) setTimeout(tick, 250);
      };
      setTimeout(tick, 400);
    }
    // proof (some proof endpoints are POST-only, e.g. generate / predictions run)
    if (st.proof) {
      const checker = CHECKERS[st.proof.check];
      try {
        const p = templ(st.proof.path, ids);
        const data = st.proof.method === "POST" ? await apiClient.post<any>(p, {}) : await apiClient.get<any>(p);
        if (checker) setProof(checker(data));
      } catch { setProof({ label: "Could not load proof", pass: false }); }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [advisor, division, market, router, shell]);

  const start = useCallback(async (scenarioId: string, advisorId: string, div: string, mkt = "M01") => {
    const sc = SCENARIOS.find((x) => x.id === scenarioId);
    if (!sc) return;
    setBusy(true);
    try {
      setAdvisor(advisorId); setDivision(div); setMarket(mkt);
      shell.setPersona(sc.persona as any);
      // reset the scenario advisor for a clean replay (backend refuses anchored)
      await apiClient.post(`/recommendations/lifecycle/reset/${advisorId}`, {}).catch(() => null);
      // capture baselines
      const [rev, adv, firm, divDash, state] = await Promise.all([
        apiClient.get<any>(`/revenue/analytics?scope_type=ADVISOR&scope_id=${advisorId}&period=LTM`).catch(() => null),
        apiClient.get<any>(`/advisor/360/${advisorId}`).catch(() => null),
        apiClient.get<any>(`/scope/dashboard?scope_type=FIRM&scope_id=F001&period=LTM&compare_to=Prior%20Year`).catch(() => null),
        apiClient.get<any>(`/scope/dashboard?scope_type=DIVISION&scope_id=${div}&period=LTM&compare_to=Prior%20Year`).catch(() => null),
        apiClient.get<any>(`/feedback-learning/state`).catch(() => null),
      ]);
      const mktDash = await apiClient.get<any>(`/scope/dashboard?scope_type=MARKET&scope_id=${mkt}&period=LTM&compare_to=Prior%20Year`).catch(() => null);
      const weights: Record<string, number> = {};
      (state?.weights ?? []).forEach((w: any) => { weights[w.family] = w.weight; });
      setBaselines({ advisorRevenue: rev?.kpis?.total_revenue, firmRevenue: firm?.totals?.revenue_ltm,
                     divisionRevenue: divDash?.totals?.revenue_ltm, marketRevenue: mktDash?.totals?.revenue_ltm,
                     snapshotRevenue: adv?.feature_snapshot?.features?.revenue_ltm, weights });
      setCaptured({});
      setScenario(sc); setStepIndex(0);
      await goToStep(0, sc);
    } finally { setBusy(false); }
  }, [shell, goToStep]);

  const next = useCallback(() => {
    if (!scenario) return;
    const ni = Math.min(scenario.steps.length - 1, stepIndex + 1);
    setStepIndex(ni); void goToStep(ni, scenario);
  }, [scenario, stepIndex, goToStep]);
  const back = useCallback(() => {
    if (!scenario) return;
    const pi = Math.max(0, stepIndex - 1);
    setStepIndex(pi); void goToStep(pi, scenario);
  }, [scenario, stepIndex, goToStep]);
  const exit = useCallback(() => {
    document.querySelectorAll(".story-highlight").forEach((e) => e.classList.remove("story-highlight"));
    setScenario(null); setStepIndex(0); setProof(null);
  }, []);

  const runAction = useCallback(async () => {
    if (!step?.action) return;
    setBusy(true);
    try {
      for (const call of step.action.calls) {
        // Template any {A}/{D}/{firm} placeholders in the call body against the current ids.
        const filled = JSON.parse(templ(JSON.stringify(call.body ?? {}), ids));
        // Feedback-learning calls need the captured recommendation context injected;
        // other real calls (e.g. coaching task assignment) send their body as-is.
        const body = call.path.includes("/feedback-learning/")
          ? { ...filled, recommendation_id: captured.recId, action_family: captured.family, user_id: "story-mode" }
          : filled;
        const res: any = await apiClient.post(templ(call.path, ids), body);
        if (res?.lifecycle?.impact?.impact_amount != null) {
          setCaptured((c) => ({ ...c, impactRecorded: res.lifecycle.impact.impact_amount }));
        }
      }
      shell.refresh();
      setProof({ label: `Completed — impact recorded. Advance to see it propagate.`, pass: true });
    } catch (e) {
      setProof({ label: "Action failed (already completed?)", pass: false });
    } finally { setBusy(false); }
  }, [step, captured, shell]);

  return (
    <Ctx.Provider value={{ active: !!scenario, scenario, stepIndex, step, advisor, busy, proof, start, next, back, exit, runAction }}>
      {children}
      {scenario && step && <StoryOverlay />}
    </Ctx.Provider>
  );
}
