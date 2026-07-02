import { test, expect } from "@playwright/test";

const routes = [
  ["/dashboard", "executive-dashboard"],
  ["/revenue-analytics", "revenue-analytics"],
  ["/advisor-360", "advisor-360"],
  ["/agp", "agp"],
  ["/what-if", "what-if"],
  ["/predictions", "predictions"],
  ["/recommendations", "recommendations"],
  ["/recommendation-roi", "recommendation-roi"],
  ["/ai-assistant", "ai-assistant"],
  ["/knowledge", "knowledge"],
  ["/graph-explorer", "graph-explorer"],
  ["/features-embeddings", "features-embeddings"],
  ["/memory-explainability", "memory-explainability"],
  ["/agents", "agents"],
  ["/data-ingestion", "data-ingestion"],
  ["/admin", "admin"]
];

for (const [route, name] of routes) {
  test(`capture ${name}`, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator("body")).toBeVisible();
    await page.screenshot({ path: `../docs/ui_runtime/screenshots/${name}.png`, fullPage: true });
  });
}
