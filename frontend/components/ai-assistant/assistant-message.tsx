import type { AssistantMessage } from "@/lib/types/ai_assistant";
import { Badge } from "@/components/ui/badge";

export function AssistantMessageBubble({ message }: { message: AssistantMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div className={isUser ? "max-w-[80%] rounded-3xl bg-primary p-4 text-primary-foreground" : "max-w-[88%] rounded-3xl border border-border/70 bg-card p-4"}>
        <div className="whitespace-pre-wrap text-sm leading-6">{message.content}</div>
        {!isUser && (
          <div className="mt-4 space-y-3">
            {message.evidence && (
              <div>
                <div className="mb-1 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">Evidence</div>
                <div className="flex flex-wrap gap-2">{message.evidence.map((item) => <Badge key={item} variant="glass">{item}</Badge>)}</div>
              </div>
            )}
            {message.toolCalls && (
              <div>
                <div className="mb-1 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">Tool Calls</div>
                <div className="flex flex-wrap gap-2">{message.toolCalls.map((item) => <Badge key={item} variant="secondary">{item}</Badge>)}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
