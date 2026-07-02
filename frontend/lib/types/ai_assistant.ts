export type AssistantMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  evidence?: string[];
  reasoningSteps?: string[];
  toolCalls?: string[];
};

export type SuggestedQuestion = {
  label: string;
  prompt: string;
};
