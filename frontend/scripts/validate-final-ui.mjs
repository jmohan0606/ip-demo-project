import fs from "fs";
import path from "path";

const routes = [
  ["Executive Dashboard", "app/(dashboard)/dashboard/page.tsx"],
  ["Revenue Analytics", "app/(dashboard)/revenue-analytics/page.tsx"],
  ["Advisor 360 / Client 360", "app/(dashboard)/advisor-360/page.tsx"],
  ["AGP Goals & Coaching", "app/(dashboard)/agp/page.tsx"],
  ["What-If Simulator", "app/(dashboard)/what-if/page.tsx"],
  ["Prediction & Forecasting", "app/(dashboard)/predictions/page.tsx"],
  ["Opportunities & Recommendations", "app/(dashboard)/recommendations/page.tsx"],
  ["Recommendation Impact / ROI", "app/(dashboard)/recommendation-roi/page.tsx"],
  ["AI Assistant", "app/(dashboard)/ai-assistant/page.tsx"],
  ["Knowledge / Playbooks / Compliance", "app/(dashboard)/knowledge/page.tsx"],
  ["Knowledge Graph Explorer", "app/(dashboard)/graph-explorer/page.tsx"],
  ["Feature Store / Embeddings / Similarity", "app/(dashboard)/features-embeddings/page.tsx"],
  ["Memory Timeline & Explainability", "app/(dashboard)/memory-explainability/page.tsx"],
  ["Agent Orchestration & Observability", "app/(dashboard)/agents/page.tsx"],
  ["Data Ingestion & Sync", "app/(dashboard)/data-ingestion/page.tsx"],
  ["Admin / Data Quality / Runtime Health", "app/(dashboard)/admin/page.tsx"]
];

const requiredCore = [
  "components/layout/app-shell.tsx",
  "components/layout/top-header.tsx",
  "components/navigation/sidebar-navigation.tsx",
  "components/status/persona-scope-selector.tsx",
  "components/status/runtime-mode-pill.tsx",
  "lib/navigation.ts",
  "lib/api/client.ts"
];

const missing = [];
for (const [label, route] of routes) {
  if (!fs.existsSync(path.join(process.cwd(), route))) {
    missing.push(`${label}: ${route}`);
  }
}
for (const file of requiredCore) {
  if (!fs.existsSync(path.join(process.cwd(), file))) {
    missing.push(file);
  }
}

const nav = fs.readFileSync(path.join(process.cwd(), "lib/navigation.ts"), "utf8");
const missingNav = routes.map(([label]) => label).filter((label) => !nav.includes(label));

if (missing.length || missingNav.length) {
  console.error("Final UI validation failed.");
  if (missing.length) {
    console.error("Missing files:");
    for (const item of missing) console.error(`- ${item}`);
  }
  if (missingNav.length) {
    console.error("Missing nav labels:");
    for (const item of missingNav) console.error(`- ${item}`);
  }
  process.exit(1);
}

console.log("Final enterprise UI consolidation validation passed.");
console.log(`Routes validated: ${routes.length}`);
