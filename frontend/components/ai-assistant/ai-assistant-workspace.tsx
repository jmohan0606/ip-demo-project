"use client";

import { useState } from "react";
import { Bot, Send, Sparkles } from "lucide-react";
import { askAssistant } from "@/lib/api/ai_assistant";
import type { AssistantMessage, SuggestedQuestion } from "@/lib/types/ai_assistant";
import { AssistantMessageBubble } from "@/components/ai-assistant/assistant-message";
import { AssistantEvidencePanel } from "@/components/ai-assistant/evidence-panel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const suggestions: SuggestedQuestion[] = [
  { label: "Revenue risk", prompt: "Why is my revenue below peer benchmark and what should I do next?" },
  { label: "NNM outflow", prompt: "Which households are driving NNM outflow and what action should I take?" },
  { label: "AGP coaching", prompt: "Why is this advisor at risk in AGP and how should MDW coach them?" },
  { label: "Recommendation evidence", prompt: "Explain the evidence behind the top recommendation." }
];

export function AiAssistantWorkspace() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "I can answer advisor performance, revenue, AGP, NNM, recommendations, memory, and evidence questions using the agentic workflow.",
      timestamp: new Date().toISOString(),
      evidence: ["Context memory", "Knowledge playbooks", "Recommendations", "Opportunities"],
      reasoningSteps: ["Waiting for user question"],
      toolCalls: ["Ready"]
    }
  ]);

  async function submit(prompt?: string) {
    const q = prompt ?? question;
    if (!q.trim()) return;

    const userMessage: AssistantMessage = { id: `user-${Date.now()}`, role: "user", content: q, timestamp: new Date().toISOString() };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setLoading(true);

    const answer = await askAssistant(q);
    setMessages((current) => [...current, answer]);
    setLoading(false);
  }

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="animate-slide-up space-y-6">
      <div>
        <Badge variant="glass">AI Assistant</Badge>
        <h2 className="mt-3 text-3xl font-black tracking-tight">Advisor Intelligence Copilot</h2>
        <p className="mt-2 text-muted-foreground">Ask questions grounded in memory, TigerGraph MCP, Chroma RAG, recommendations, opportunities, predictions and explainability.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_.85fr]">
        <Card className="min-h-[680px]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Bot className="h-5 w-5 text-primary" /> Conversation</CardTitle>
            <CardDescription>Separate assistant page, not a dashboard tile.</CardDescription>
          </CardHeader>
          <CardContent className="flex min-h-[560px] flex-col">
            <div className="flex-1 space-y-4 overflow-y-auto rounded-3xl border border-border/70 bg-muted/30 p-4">
              {messages.map((message) => <AssistantMessageBubble key={message.id} message={message} />)}
              {loading && <div className="rounded-3xl border border-border/70 bg-card p-4 text-sm text-muted-foreground">Thinking through context, tools, evidence and recommendations...</div>}
            </div>

            <div className="mt-4 flex gap-2">
              <input
                className="flex-1 rounded-2xl border border-border bg-background px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask about revenue, NNM, AUM, AGP, recommendations, or why/how evidence..."
                onKeyDown={(event) => { if (event.key === "Enter") submit(); }}
              />
              <Button variant="premium" className="gap-2" onClick={() => submit()} disabled={loading}>
                <Send className="h-4 w-4" />
                Ask
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-primary" /> Suggested Questions</CardTitle>
              <CardDescription>Demo-ready prompts for client walkthrough.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {suggestions.map((item) => (
                <button key={item.label} onClick={() => submit(item.prompt)} className="w-full rounded-2xl border border-border/70 bg-background/70 p-3 text-left text-sm transition hover:bg-accent">
                  <div className="font-bold">{item.label}</div>
                  <div className="text-muted-foreground">{item.prompt}</div>
                </button>
              ))}
            </CardContent>
          </Card>

          <AssistantEvidencePanel message={lastAssistant} />
        </div>
      </div>
    </div>
  );
}
