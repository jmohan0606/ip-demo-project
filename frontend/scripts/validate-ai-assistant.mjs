import fs from "fs";
const files = [
  "components/ai-assistant/ai-assistant-workspace.tsx",
  "components/ai-assistant/assistant-message.tsx",
  "components/ai-assistant/evidence-panel.tsx",
  "app/(dashboard)/ai-assistant/page.tsx",
  "lib/api/ai_assistant.ts",
  "lib/types/ai_assistant.ts"
];
for (const f of files) {
  if (!fs.existsSync(f)) {
    console.error(`Missing ${f}`);
    process.exit(1);
  }
}
const page = fs.readFileSync("components/ai-assistant/ai-assistant-workspace.tsx", "utf8");
for (const term of ["Advisor Intelligence Copilot", "Suggested Questions", "Evidence & Reasoning", "Tool Calls"]) {
  if (!page.includes(term) && !fs.readFileSync("components/ai-assistant/evidence-panel.tsx", "utf8").includes(term) && !fs.readFileSync("components/ai-assistant/assistant-message.tsx", "utf8").includes(term)) {
    console.error(`Missing term ${term}`);
    process.exit(1);
  }
}
console.log("AI Assistant validation passed");
