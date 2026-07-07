import { chromium } from "/workspaces/ip-demo-project/frontend/node_modules/playwright/index.mjs";
const OUT = new URL("../docs/qa_screenshots/session16/", import.meta.url).pathname;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
page.setDefaultTimeout(180000);
await page.goto("http://127.0.0.1:3000/ai-assistant", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(3000);
// set persona to DDW → scope becomes Division D01
await page.selectOption("select >> nth=0", "DDW");
await page.waitForTimeout(1500);
await page.waitForSelector("text=Which of my advisors need attention", { timeout: 30000 });
await page.click("text=Which of my advisors need attention");
// wait for the real Claude answer to render
await page.waitForSelector("text=Sources", { timeout: 180000 }).catch(() => {});
await page.waitForTimeout(45000);
await page.screenshot({ path: OUT + "assistant_ddw_division_scope.png", fullPage: true });
console.log("captured");
await browser.close();
