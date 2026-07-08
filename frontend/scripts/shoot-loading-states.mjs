import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = "../docs/qa_screenshots/session18";
mkdirSync(OUT, { recursive: true });
const BASE = "http://127.0.0.1:3000";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function shoot(page, name) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log("shot:", name);
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });

// ---- 1. Revenue Trend Explorer: hold /revenue/trend to capture the skeleton ----
{
  const page = await ctx.newPage();
  let release;
  const gate = new Promise((r) => (release = r));
  await page.route("**/revenue/trend**", async (route) => {
    await gate; // hold until we've screenshotted the loading state
    await route.continue();
  });
  await page.goto(`${BASE}/revenue-analytics`, { waitUntil: "domcontentloaded" });
  await sleep(2500);
  // scroll the trend explorer into view (bottom of page)
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(600);
  await shoot(page, "revenue-trend-LOADING");
  release();
  await sleep(3500);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(800);
  await shoot(page, "revenue-trend-LOADED");
  await page.close();
}

// ---- 2. Executive Dashboard: hold the AI insight fetch to capture AiCardSkeleton ----
{
  const page = await ctx.newPage();
  let release;
  const gate = new Promise((r) => (release = r));
  await page.route(/\/(advisor\/360\/[^/]+\/ai|.*ai-insight.*|scope.*ai.*)/i, async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded" });
  await sleep(3000);
  await shoot(page, "dashboard-AI-LOADING");
  release();
  await sleep(4000);
  await shoot(page, "dashboard-AI-LOADED");
  await page.close();
}

// ---- 3. Executive Dashboard AI ERROR state: abort the AI insight fetch ----
{
  const page = await ctx.newPage();
  await page.route(/\/(advisor\/360\/[^/]+\/ai|.*ai-insight.*|scope.*ai.*)/i, (route) => route.abort());
  await page.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded" });
  await sleep(4000);
  await shoot(page, "dashboard-AI-ERROR");
  await page.close();
}

// ---- 4. Agent Orchestration: hold the agentic run to capture LoadingState ----
{
  const page = await ctx.newPage();
  let release;
  const gate = new Promise((r) => (release = r));
  await page.route(/\/(agentic|orchestration|agent).*run|.*\/run\b/i, async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto(`${BASE}/agents`, { waitUntil: "domcontentloaded" });
  await sleep(3000);
  await shoot(page, "orchestration-RUN-LOADING");
  release();
  await sleep(5000);
  await shoot(page, "orchestration-RUN-LOADED");
  await page.close();
}

await browser.close();
console.log("done ->", OUT);
