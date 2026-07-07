import { chromium } from "/workspaces/ip-demo-project/frontend/node_modules/playwright/index.mjs";
import { mkdirSync } from "node:fs";
const OUT = new URL("../docs/qa_screenshots/session16/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(120000);
await page.goto("http://127.0.0.1:3000/story", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(4000);
await page.screenshot({ path: OUT + "story_launch_scenarios.png", fullPage: true });
console.log("story launch captured");

// launch the division journey and capture the first overlay step
const divBtn = page.locator("text=Division").first();
await page.screenshot({ path: OUT + "story_launch_pre.png", fullPage: false });
const launchButtons = page.locator("button:has-text('Start')");
console.log("start buttons:", await launchButtons.count());
await browser.close();
