"use client";
import { useState } from "react";
import { PlayCircle, Save, Sparkles } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { runWhatIfScenario } from "@/lib/api/integrated-ui";
import { AssumptionSlider } from "@/components/whatif/assumption-slider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";

export function WhatIfSimulatorClient() {
  const context = useApiContextPayload();
  const [assumptions, setAssumptions] = useState({
    meeting_increase_pct: 12,
    prospect_conversion_increase_pct: 8,
    managed_revenue_shift_pct: 6,
    nnm_increase_pct: 5,
    aum_increase_pct: 3
  });
  const [result, setResult] = useState<any | null>(null);
  const update = (key: string, value: number) => setAssumptions((current) => ({ ...current, [key]: value }));
  async function run() { setResult(await runWhatIfScenario(context, assumptions)); }

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div><Badge variant="glass">Scenario Simulator</Badge><h2 className="mt-2 text-[22px] font-black">What-If Simulator Using Current Selected Data</h2><p className="text-[12px] text-muted-foreground">Runs against selected persona/scope/period and shows projected change.</p></div>
        <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={run}><PlayCircle className="h-4 w-4" />Run Scenario</Button>
      </div>
      <div className="grid gap-3 xl:grid-cols-[.9fr_1.1fr]">
        <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Scenario Levers</CardTitle></CardHeader><CardContent className="space-y-2 p-3">
          <AssumptionSlider label="Meeting Frequency Increase" value={assumptions.meeting_increase_pct} onChange={(v) => update("meeting_increase_pct", v)} />
          <AssumptionSlider label="Prospect Conversion Increase" value={assumptions.prospect_conversion_increase_pct} onChange={(v) => update("prospect_conversion_increase_pct", v)} />
          <AssumptionSlider label="Managed Revenue Mix Shift" value={assumptions.managed_revenue_shift_pct} onChange={(v) => update("managed_revenue_shift_pct", v)} />
          <AssumptionSlider label="NNM Improvement" value={assumptions.nnm_increase_pct} onChange={(v) => update("nnm_increase_pct", v)} />
          <AssumptionSlider label="AUM Growth" value={assumptions.aum_increase_pct} onChange={(v) => update("aum_increase_pct", v)} />
        </CardContent></Card>
        <Card className="bg-ai-soft"><CardHeader className="p-3"><CardTitle className="text-[13px]">Projected Impact</CardTitle></CardHeader><CardContent className="space-y-3 p-3">
          {!result ? <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">Run scenario to see projected changes.</div> : (
            <>
              {["revenue", "nnm", "aum"].map((m) => <div key={m} className="grid grid-cols-4 rounded-xl border bg-background/80 p-3 text-[12px]"><div className="font-bold uppercase">{m}</div><div>Baseline<br/><strong>{formatCurrency(result.baseline[m])}</strong></div><div>Projected<br/><strong>{formatCurrency(result.projected[m])}</strong></div><Badge variant="success">+{formatCurrency(result.changes[`${m}_delta`])}</Badge></div>)}
              <div className="rounded-xl border bg-good-soft p-3 text-[12px]">AGP Goal changes from {result.baseline.agp_goal}% to {result.projected.agp_goal.toFixed(1)}%.</div>
              <div className="flex gap-2"><Button className="h-8 gap-1 text-[12px]"><Sparkles className="h-4 w-4" />Convert to Recommendation</Button><Button variant="outline" className="h-8 gap-1 text-[12px]"><Save className="h-4 w-4" />Save to Memory</Button></div>
            </>
          )}
        </CardContent></Card>
      </div>
    </div>
  );
}
