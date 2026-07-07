import { chromium } from "/workspaces/ip-demo-project/frontend/node_modules/playwright/index.mjs";
import { mkdirSync } from "node:fs";
const OUT = new URL("../docs/qa_screenshots/session16/sweep/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const pages = [
  ["revenue_analytics", "/revenue-analytics"],
  ["advisor_360", "/advisor-360"],
  ["opps_recs", "/recommendations"],
  ["rec_impact", "/recommendation-roi"],
  ["crm", "/crm-activities"],
  ["client_intel", "/client-360"],
  ["coaching", "/coaching-reviews"],
  ["peer_benchmarking", "/peer-benchmarking"],
  ["what_if", "/what-if"],
  ["assistant", "/ai-assistant"],
];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(60000);
for (const [name, path] of pages) {
  try {
    await page.goto("http://127.0.0.1:3000" + path, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(7000);
    await page.screenshot({ path: OUT + name + ".png", fullPage: true });
    console.log("ok", name);
  } catch (e) { console.log("fail", name, String(e).slice(0, 120)); }
}
await browser.close();
