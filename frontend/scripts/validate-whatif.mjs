import fs from "fs";
const files = [
  "components/whatif/whatif-simulator-client.tsx",
  "components/whatif/assumption-slider.tsx",
  "components/whatif/impact-comparison.tsx",
  "app/(dashboard)/what-if/page.tsx",
  "lib/api/whatif.ts",
  "lib/types/whatif.ts"
];
for (const f of files) {
  if (!fs.existsSync(f)) {
    console.error(`Missing ${f}`);
    process.exit(1);
  }
}
const page = fs.readFileSync("components/whatif/whatif-simulator-client.tsx", "utf8");
for (const term of ["Scenario Assumptions", "Baseline vs Scenario Impact", "AI Scenario Explanation", "Saved Scenarios", "Convert to Recommendation"]) {
  if (!page.includes(term)) {
    console.error(`Missing term ${term}`);
    process.exit(1);
  }
}
console.log("What-if simulator validation passed");
