import fs from "node:fs";
import path from "node:path";
const required = [
  "package.json","next.config.mjs","tailwind.config.ts","components.json","app/layout.tsx",
  "app/(dashboard)/layout.tsx","app/(dashboard)/dashboard/page.tsx",
  "components/layout/app-shell.tsx","components/navigation/sidebar-navigation.tsx",
  "components/status/persona-scope-selector.tsx","components/loading/global-loading-overlay.tsx",
  "lib/navigation.ts","lib/api/client.ts","lib/api/endpoints.ts"
];
const missing = required.filter((item) => !fs.existsSync(path.join(process.cwd(), item)));
if (missing.length) { console.error("Missing required UI architecture files:"); for (const item of missing) console.error(`- ${item}`); process.exit(1); }
const navigation = fs.readFileSync(path.join(process.cwd(), "lib/navigation.ts"), "utf8");
const requiredMenus = [
  "Executive Dashboard","Revenue Analytics","Advisor 360 / Client 360","AGP Goals & Coaching",
  "What-If Simulator","Opportunities & Recommendations","Recommendation Impact / ROI","AI Assistant",
  "Knowledge / Playbooks / Compliance","Knowledge Graph Explorer","Feature Store / Embeddings / Similarity",
  "Memory Timeline & Explainability","Agent Orchestration & Observability","Data Ingestion & Sync",
  "Admin / Data Quality / Runtime Health"
];
const missingMenus = requiredMenus.filter((menu) => !navigation.includes(menu));
if (missingMenus.length) { console.error("Missing required menus:"); for (const item of missingMenus) console.error(`- ${item}`); process.exit(1); }
console.log("UI architecture validation passed.");
console.log(`Menus validated: ${requiredMenus.length}`);
