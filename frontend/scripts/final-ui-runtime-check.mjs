import fs from "fs";
import path from "path";

const routes = [
  ["/dashboard", "Executive Dashboard"],
  ["/revenue-analytics", "Revenue Analytics"],
  ["/advisor-360", "Advisor 360 / Client 360"],
  ["/agp", "AGP Goals & Coaching"],
  ["/what-if", "What-If Simulator"],
  ["/predictions", "Prediction & Forecasting"],
  ["/recommendations", "Opportunities & Recommendations"],
  ["/recommendation-roi", "Recommendation Impact / ROI"],
  ["/ai-assistant", "AI Assistant"],
  ["/knowledge", "Knowledge / Playbooks / Compliance"],
  ["/graph-explorer", "Knowledge Graph Explorer"],
  ["/features-embeddings", "Feature Store / Embeddings / Similarity"],
  ["/memory-explainability", "Memory Timeline & Explainability"],
  ["/agents", "Agent Orchestration & Observability"],
  ["/data-ingestion", "Data Ingestion & Sync"],
  ["/admin", "Admin / Data Quality / Runtime Health"]
];

const checks = [];
function exists(file) {
  const ok = fs.existsSync(path.join(process.cwd(), file));
  checks.push({ file, status: ok ? "passed" : "failed" });
  return ok;
}

exists("package.json");
exists("next.config.mjs");
exists("tailwind.config.ts");
exists("components/layout/app-shell.tsx");
exists("components/navigation/sidebar-navigation.tsx");
exists("lib/navigation.ts");

for (const [href] of routes) {
  const routeFile = href === "/dashboard"
    ? "app/(dashboard)/dashboard/page.tsx"
    : `app/(dashboard)${href}/page.tsx`;
  exists(routeFile);
}

const failed = checks.filter((c) => c.status === "failed");
const report = {
  status: failed.length === 0 ? "passed" : "failed",
  routeCount: routes.length,
  checks,
  failed
};

fs.mkdirSync("../docs/ui_runtime", { recursive: true });
fs.writeFileSync("../docs/ui_runtime/final_ui_runtime_check.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (failed.length) process.exit(1);
