import fs from "fs";
const files = [
  "components/predictions/prediction-workspace.tsx",
  "components/predictions/forecast-chart.tsx",
  "components/predictions/prediction-model-card.tsx",
  "components/predictions/prediction-drivers-panel.tsx",
  "app/(dashboard)/predictions/page.tsx",
  "lib/api/predictions_workspace.ts",
  "lib/types/predictions_workspace.ts"
];
for (const f of files) {
  if (!fs.existsSync(f)) {
    console.error(`Missing ${f}`);
    process.exit(1);
  }
}
const page = fs.readFileSync("components/predictions/prediction-workspace.tsx", "utf8");
for (const term of ["Revenue Forecast", "Prediction Drivers", "Prediction Models", "Explainability Summary", "GNN"]) {
  if (!page.includes(term)) {
    console.error(`Missing ${term}`);
    process.exit(1);
  }
}
console.log("Prediction workspace validation passed");
