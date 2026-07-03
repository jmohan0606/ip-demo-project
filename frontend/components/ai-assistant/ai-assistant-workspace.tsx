"use client";

import { useState } from "react";

import { AiContentCard } from "@/components/patterns/ai-content-card";
import {
  askChat,
  runAgentic,
  type AgenticAnswer,
  type ChatAnswer,
} from "@/lib/api/assistant";
import { colors, type } from "@/styles/tokens";

const SUGGESTIONS = [
  "Why is this advisor below the peer revenue benchmark?",
  "What is driving the AGP off-track risk and how do we recover it?",
  "Explain the evidence behind the top recommendation.",
  "Which CRM follow-ups are overdue and most valuable?",
];

type Turn =
  | { role: "user"; content: string }
  | { role: "chat"; data: ChatAnswer }
  | { role: "agentic"; data: AgenticAnswer };

export function AiAssistantWorkspace({ advisorId = "A001" }: { advisorId?: string }) {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<"chat" | "agentic">("chat");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(text?: string) {
    const q = (text ?? question).trim();
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    setTurns((cur) => [...cur, { role: "user", content: q }]);
    setQuestion("");
    try {
      if (mode === "agentic") {
        const data = await runAgentic(q, advisorId);
        setTurns((cur) => [...cur, { role: "agentic", data }]);
      } else {
        const data = await askChat(q, advisorId);
        setTurns((cur) => [...cur, { role: "chat", data }]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assistant request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>AI Assistant</h1>
          <p className={type.body} style={{ color: colors.text.secondary }}>
            Context-aware advisor Q&amp;A for {advisorId}. Chat answers ground in memory, knowledge and
            insights; agentic mode exposes the multi-agent reasoning path, evidence and confidence.
          </p>
        </div>
        <div className="flex overflow-hidden rounded-lg border" style={{ borderColor: colors.surface.border }}>
          {(["chat", "agentic"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className="px-3 py-1.5 text-[12px] font-semibold"
              style={{
                backgroundColor: mode === m ? colors.primary : "white",
                color: mode === m ? "white" : colors.text.secondary,
              }}
            >
              {m === "agentic" ? "Agentic reasoning" : "Chat"}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => void submit(s)}
            disabled={busy}
            className="rounded-full border px-3 py-1 text-[12px] hover:bg-white disabled:opacity-50"
            style={{ borderColor: colors.surface.border, color: colors.text.secondary }}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {turns.map((turn, index) => {
          if (turn.role === "user") {
            return (
              <div key={index} className="flex justify-end">
                <div className="max-w-[80%] rounded-xl px-3 py-2 text-[13px] text-white" style={{ backgroundColor: colors.primary }}>
                  {turn.content}
                </div>
              </div>
            );
          }
          if (turn.role === "chat") return <ChatTurn key={index} data={turn.data} />;
          return <AgenticTurn key={index} data={turn.data} />;
        })}
        {busy ? <p className={type.data} style={{ color: colors.text.muted }}>Thinking…</p> : null}
        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">{error}</div>
        ) : null}
      </div>

      <div className="sticky bottom-0 flex gap-2 rounded-xl border bg-white p-2 shadow-sm" style={{ borderColor: colors.surface.border }}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder={`Ask about advisor ${advisorId}…`}
          className="flex-1 rounded-lg px-3 py-2 text-[13px] outline-none"
          style={{ color: colors.text.primary }}
        />
        <button
          onClick={() => submit()}
          disabled={busy}
          className="rounded-lg px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-50"
          style={{ backgroundColor: colors.primary }}
        >
          Send
        </button>
      </div>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className={type.label} style={{ color: colors.text.muted }}>confidence</span>
      <div className="h-2 w-24 overflow-hidden rounded-full" style={{ backgroundColor: "#F1F5F9" }}>
        <div className="h-full rounded-full" style={{ width: `${value * 100}%`, backgroundColor: colors.positive }} />
      </div>
      <span className={`font-mono ${type.data}`} style={{ color: colors.text.secondary }}>{(value * 100).toFixed(0)}%</span>
    </div>
  );
}

function ReasoningSteps({ steps }: { steps: string[] }) {
  return (
    <ol className="space-y-1">
      {steps.map((step, i) => (
        <li key={i} className="flex gap-2">
          <span
            className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] font-bold text-white"
            style={{ backgroundColor: colors.aiAccent }}
          >
            {i + 1}
          </span>
          <span className={type.data} style={{ color: colors.text.secondary }}>{step}</span>
        </li>
      ))}
    </ol>
  );
}

function ChatTurn({ data }: { data: ChatAnswer }) {
  return (
    <AiContentCard title="Assistant" footer={<ConfidenceBar value={data.confidence} />}>
      <p className={type.body} style={{ color: colors.text.primary, whiteSpace: "pre-wrap" }}>{data.answer}</p>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <div className={type.label} style={{ color: colors.text.muted }}>Reasoning</div>
          <div className="mt-1"><ReasoningSteps steps={data.reasoning_steps} /></div>
        </div>
        <div>
          <div className={type.label} style={{ color: colors.text.muted }}>Evidence / context ({data.context_items.length})</div>
          <div className="mt-1 space-y-1">
            {data.context_items.map((item, i) => (
              <div key={i} className="rounded-md border px-2 py-1" style={{ borderColor: colors.surface.border }}>
                <span className="font-semibold uppercase tracking-wide" style={{ color: colors.aiAccent, fontSize: 10 }}>
                  {item.source}
                </span>
                <span className={`ml-1 ${type.data}`} style={{ color: colors.text.secondary }}>{item.title}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AiContentCard>
  );
}

function AgenticTurn({ data }: { data: AgenticAnswer }) {
  return (
    <AiContentCard
      title={`Agentic workflow · final agent: ${data.final_agent}`}
      footer={<ConfidenceBar value={data.confidence} />}
    >
      <p className={type.body} style={{ color: colors.text.primary, whiteSpace: "pre-wrap" }}>{data.answer}</p>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <div className={type.label} style={{ color: colors.text.muted }}>Agent reasoning path</div>
          <div className="mt-1"><ReasoningSteps steps={data.reasoning_steps} /></div>
        </div>
        <div>
          <div className={type.label} style={{ color: colors.text.muted }}>
            Evidence {data.evidence.length} · tasks {data.tasks.length} · recs {data.recommendations.length} ·
            opps {data.opportunities.length} · preds {data.predictions.length}
          </div>
          <pre
            className="mt-1 max-h-56 overflow-auto rounded-lg border p-2 font-mono text-[10px] leading-4"
            style={{ borderColor: colors.surface.border, backgroundColor: colors.surface.canvas, color: colors.text.secondary }}
          >
            {JSON.stringify(data.evidence, null, 2)}
          </pre>
        </div>
      </div>
    </AiContentCard>
  );
}
