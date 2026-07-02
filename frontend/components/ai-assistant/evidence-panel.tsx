import type { AssistantMessage } from "@/lib/types/ai_assistant";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function AssistantEvidencePanel({ message }: { message?: AssistantMessage }) {
  const reasoning = message?.reasoningSteps ?? ["Ask a question to see reasoning steps."];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Evidence & Reasoning</CardTitle>
        <CardDescription>Context, tool calls, memory and playbook evidence used by the assistant.</CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="list-decimal space-y-2 pl-5 text-sm text-muted-foreground">
          {reasoning.map((step) => <li key={step}>{step}</li>)}
        </ol>
      </CardContent>
    </Card>
  );
}
