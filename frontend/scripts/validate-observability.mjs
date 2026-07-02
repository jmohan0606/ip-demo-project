import fs from "fs";
const files = [
  "components/observability/system-observability-workspace.tsx",
  "components/observability/service-health-grid.tsx",
  "components/observability/agent-metrics-table.tsx",
  "components/observability/workflow-trace-list.tsx",
  "components/observability/error-events-panel.tsx",
  "app/(dashboard)/agents/page.tsx",
  "lib/api/observability.ts",
  "lib/types/observability.ts"
];
for (const f of files) {
  if (!fs.existsSync(f)) {
    console.error(`Missing ${f}`);
    process.exit(1);
  }
}
const page = fs.readFileSync("components/observability/system-observability-workspace.tsx", "utf8");
for (const term of ["Service Health Dashboard", "Agent Operations", "LangGraph Workflow Traces", "Token, Cost & Usage", "Error Analysis & Remediation", "Audit & Governance Coverage"]) {
  if (!page.includes(term)) {
    console.error(`Missing ${term}`);
    process.exit(1);
  }
}
console.log("System observability validation passed");
