import fs from "fs";

const pages = [
  "Executive Dashboard",
  "Revenue Analytics",
  "Advisor 360 / Client 360",
  "AGP Goals & Coaching",
  "What-If Simulator",
  "Prediction & Forecasting",
  "Opportunities & Recommendations",
  "Recommendation Impact / ROI",
  "AI Assistant",
  "Knowledge / Playbooks / Compliance",
  "Knowledge Graph Explorer",
  "Feature Store / Embeddings / Similarity",
  "Memory Timeline & Explainability",
  "Agent Orchestration & Observability",
  "Data Ingestion & Sync",
  "Admin / Data Quality / Runtime Health"
];

const checklist = {
  status: "ready_for_manual_screenshot_review",
  instruction: "Run the React app, capture each route, and compare against approved visual style.",
  reviewItems: [
    "Sidebar matches approved enterprise layout",
    "Top header has persona/scope/period controls",
    "Cards use consistent spacing, radius and visual hierarchy",
    "Loading/skeleton states exist for async pages",
    "Evidence/reasoning panels are visible where required",
    "Graph explorer renders canvas",
    "AI Assistant is a separate page",
    "No Streamlit UI dependency is required for React UI"
  ],
  pages
};

fs.mkdirSync("../docs/ui_runtime", { recursive: true });
fs.writeFileSync("../docs/ui_runtime/screenshot_review_checklist.json", JSON.stringify(checklist, null, 2));
console.log(JSON.stringify(checklist, null, 2));
