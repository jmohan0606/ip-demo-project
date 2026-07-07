// Session-16 REQ-1 verification screenshots: Executive Dashboard at FIRM and
// ADVISOR scope, after the real Claude AI insight has rendered.
import { chromium } from "/workspaces/ip-demo-project/frontend/node_modules/playwright/index.mjs";
import { mkdirSync } from "node:fs";

const OUT = new URL("../docs/qa_screenshots/session16/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(180000);

// ---- FIRM scope (default) ----
await page.goto("http://127.0.0.1:3000/dashboard", { waitUntil: "domcontentloaded" });
await page.waitForSelector("text=Key Drivers", { timeout: 180000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: OUT + "dashboard_firm_scope.png", fullPage: true });
console.log("firm scope captured");

// ---- ADVISOR scope via persona selector ----
await page.selectOption("select >> nth=0", "Advisor");
await page.waitForTimeout(1000);
await page.waitForSelector("text=Revenue / Household", { timeout: 180000 });
await page.waitForSelector("text=GNN peer group", { timeout: 180000 });
await page.waitForSelector("text=Key Drivers", { timeout: 180000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: OUT + "dashboard_advisor_scope.png", fullPage: true });
console.log("advisor scope captured");

await browser.close();
