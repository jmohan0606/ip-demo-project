import { chromium } from "/workspaces/ip-demo-project/frontend/node_modules/playwright/index.mjs";
const OUT = "/workspaces/ip-demo-project/docs/qa_screenshots/session17/";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
page.setDefaultTimeout(60000);
await page.goto("http://127.0.0.1:3000/data-ingestion", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(8000);
await page.screenshot({ path: OUT + "ingestion_before_runall.png", fullPage: true });
// click Run All Ingestion
await page.getByText("Run All Ingestion").click();
await page.waitForTimeout(6000);
await page.screenshot({ path: OUT + "ingestion_runall_progress.png", fullPage: true });
// wait for completion (skips are fast)
for (let i = 0; i < 40; i++) {
  const done = await page.locator("text=/192\\/192 entities/").count();
  if (done > 0) break;
  await page.waitForTimeout(3000);
}
await page.waitForTimeout(2000);
await page.screenshot({ path: OUT + "ingestion_runall_complete.png", fullPage: true });
console.log("done");
await browser.close();
