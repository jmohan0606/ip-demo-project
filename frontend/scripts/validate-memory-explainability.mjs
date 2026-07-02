import fs from "fs";
const files = [
  "components/memory-explainability/memory-explainability-workspace.tsx",
  "components/memory-explainability/memory-timeline.tsx",
  "components/memory-explainability/explainability-path.tsx",
  "components/memory-explainability/agent-trace-panel.tsx",
  "components/memory-explainability/tool-call-audit.tsx",
  "components/memory-explainability/learning-loop-panel.tsx",
  "app/(dashboard)/memory-explainability/page.tsx",
  "lib/api/memory_explainability.ts",
  "lib/types/memory_explainability.ts"
];
for (const f of files) {
  if (!fs.existsSync(f)) {
    console.error(`Missing ${f}`);
    process.exit(1);
  }
}
const page = fs.readFileSync("components/memory-explainability/memory-explainability-workspace.tsx", "utf8");
for (const term of ["Memory Timeline", "Recommendation Explainability Path", "Agent Execution Trace", "Tool Call Explorer", "Memory Learning Loop", "Evidence Coverage"]) {
  if (!page.includes(term)) {
    console.error(`Missing ${term}`);
    process.exit(1);
  }
}
console.log("Memory explainability validation passed");
