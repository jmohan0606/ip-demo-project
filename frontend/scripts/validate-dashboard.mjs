import fs from "node:fs";
import path from "node:path";

const required = [
  "components/dashboard/executive-dashboard-client.tsx",
  "components/dashboard/insights-coaching-panel.tsx",
  "components/dashboard/performer-table.tsx",
  "components/dashboard/executive-dashboard-skeleton.tsx",
  "components/charts/revenue-trend-chart.tsx",
  "components/charts/product-mix-chart.tsx",
  "lib/api/dashboard.ts",
  "lib/types/dashboard.ts",
  "app/(dashboard)/dashboard/page.tsx"
];

const missing = required.filter((file) => !fs.existsSync(path.join(process.cwd(), file)));
if (missing.length) {
  console.error("Missing dashboard files:");
  for (const file of missing) console.error(`- ${file}`);
  process.exit(1);
}

const dashboard = fs.readFileSync(path.join(process.cwd(), "components/dashboard/executive-dashboard-client.tsx"), "utf8");
const requiredTerms = ["Revenue Trend", "Insights & Coaching", "Product Revenue Mix", "Top Performers", "Bottom Performers"];
const missingTerms = requiredTerms.filter((term) => !dashboard.includes(term));
if (missingTerms.length) {
  console.error("Missing dashboard functionality:", missingTerms);
  process.exit(1);
}

console.log("Executive dashboard validation passed.");
