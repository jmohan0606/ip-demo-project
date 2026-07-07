import { chromium } from "/workspaces/ip-demo-project/frontend/node_modules/playwright/index.mjs";
const OUT = "/workspaces/ip-demo-project/docs/qa_screenshots/session17/";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
page.setDefaultTimeout(120000);
await page.goto("http://127.0.0.1:3000/revenue-analytics", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(30000); // trend endpoint makes real Claude calls per period
const el = page.locator("text=Revenue Trend Explorer").first();
await el.scrollIntoViewIfNeeded();
await page.waitForTimeout(2000);
await page.screenshot({ path: OUT + "trend_explorer_bullets.png", fullPage: false });
// scroll further to capture the per-period breakdown
await page.mouse.wheel(0, 700);
await page.waitForTimeout(1000);
await page.screenshot({ path: OUT + "trend_explorer_breakdown.png", fullPage: false });
console.log("done");
await browser.close();
