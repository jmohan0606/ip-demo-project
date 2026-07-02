"use client";

import { useEffect, useState } from "react";
import { Bot, BrainCircuit, PlayCircle, ShieldCheck } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { askActivatedAssistant, fetchLlmActivationStatus, generateRecommendationNarrative } from "@/lib/api/llm-activation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function LlmActivationWorkspace() {
  const context = useApiContextPayload();
  const [status, setStatus] = useState<any | null>(null);
  const [question, setQuestion] = useState("Why did revenue decline and what should I do next?");
  const [answer, setAnswer] = useState<any | null>(null);
  const [narrative, setNarrative] = useState<any | null>(null);

  async function refresh() {
    setStatus(await fetchLlmActivationStatus());
  }

  async function ask() {
    setAnswer(await askActivatedAssistant(context, question));
  }

  async function generateNarrative() {
    setNarrative(await generateRecommendationNarrative(context));
  }

  useEffect(() => { refresh(); }, []);

  const llm = status?.llm_runtime ?? status?.data?.llm_runtime;

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <Badge variant="glass">Real Azure OpenAI / LLM Agent Activation</Badge>
          <h2 className="mt-2 text-[22px] font-black">LLM Reasoning, AI Assistant & Agent Narratives</h2>
          <p className="text-[12px] text-muted-foreground">Azure OpenAI first, local mock fallback, memory/context grounding, and answer writeback.</p>
        </div>
        <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={refresh}>
          <ShieldCheck className="h-4 w-4" />Refresh Status
        </Button>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <Card className={llm?.active_mode === "azure_openai" ? "bg-good-soft" : "bg-warn-soft"}>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><BrainCircuit className="h-4 w-4" />LLM Runtime</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3 text-[12px]">
            <div>Strategy: <strong>{llm?.strategy ?? "loading"}</strong></div>
            <div>Active mode: <strong>{llm?.active_mode}</strong></div>
            <div>Azure available: <strong>{String(llm?.azure_openai_available)}</strong></div>
            <div>Mock available: <strong>{String(llm?.mock_available)}</strong></div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Bot className="h-4 w-4" />Ask AI Assistant</CardTitle></CardHeader>
          <CardContent className="space-y-3 p-3">
            <textarea className="h-24 w-full rounded-lg border p-3 text-[12px]" value={question} onChange={(e) => setQuestion(e.target.value)} />
            <div className="flex gap-2">
              <Button className="h-8 gap-2 text-[12px]" onClick={ask}><PlayCircle className="h-4 w-4" />Ask</Button>
              <Button variant="outline" className="h-8 gap-2 text-[12px]" onClick={generateNarrative}><PlayCircle className="h-4 w-4" />Generate Recommendation Narrative</Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Assistant Answer</CardTitle></CardHeader>
          <CardContent className="p-3">
            {answer ? (
              <div className="space-y-3">
                <div className="rounded-xl border bg-ai-soft p-3 text-[12px] whitespace-pre-wrap">{answer.answer}</div>
                <pre className="max-h-[300px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(answer.agent_trace, null, 2)}</pre>
              </div>
            ) : <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">Ask a question to test the activated LLM agent.</div>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="p-3"><CardTitle className="text-[13px]">Recommendation Narrative</CardTitle></CardHeader>
          <CardContent className="p-3">
            {narrative ? <pre className="max-h-[420px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(narrative, null, 2)}</pre> : <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">Generate recommendation narrative.</div>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
