// REQ-2 evidence: user-reachable path from a figure to its real model/reasoning.
import { chromium } from "/workspaces/ip-demo-project/frontend/node_modules/playwright/index.mjs";
import { mkdirSync } from "node:fs";

const OUT = new URL("../docs/qa_screenshots/session16/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(180000);

await page.goto("http://127.0.0.1:3000/dashboard", { waitUntil: "domcontentloaded" });
await page.waitForSelector("text=Overview", { timeout: 180000 });
await page.waitForTimeout(3000);
await page.selectOption("select >> nth=0", "Advisor");
await page.waitForSelector("text=Avery Diaz Overview", { timeout: 60000 });
await page.waitForSelector("text=GNN peer group", { timeout: 180000 });
await page.waitForTimeout(1000);

const buttons = page.locator('button[aria-label="How was this computed?"]');
const n = await buttons.count();
console.log("trace buttons on page:", n);

async function shoot(idx, file) {
  const b = buttons.nth(idx);
  await b.scrollIntoViewIfNeeded();
  await b.click();
  await page.waitForSelector("text=Why this number");
  await page.waitForTimeout(400);
  await page.screenshot({ path: OUT + file, fullPage: false });
  await page.keyboard.press("Escape");
  await b.click({ force: true }); // toggle closed
  await page.waitForTimeout(300);
  console.log(file, "captured");
}

// tile order: 0=total_revenue … 6=agp_risk; benchmark card's button comes after the 9 tiles
await shoot(0, "req2_total_revenue_trace.png");
await shoot(6, "req2_agp_risk_trace.png");
// find the benchmark button: it's inside the card that also contains "GNN peer group"
const benchIdx = n - 2; // benchmark card trace button precedes the transactions card button
await shoot(benchIdx, "req2_benchmark_gnn_trace.png");

// The destination of the AGP-risk trace link: /predictions model detail
await page.goto("http://127.0.0.1:3000/predictions", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(8000);
await page.screenshot({ path: OUT + "req2_predictions_model_detail.png", fullPage: true });
console.log("predictions page captured");

await browser.close();
