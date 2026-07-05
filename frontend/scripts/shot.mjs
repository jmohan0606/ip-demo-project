// Usage: node scripts/shot.mjs <route> <outName> [waitMs]
// Captures a full-page screenshot of a dashboard route and prints console errors.
// Screenshots go to docs/qa_screenshots/ (standing rule: never /tmp).
import { chromium } from "playwright";
import path from "path";
import fs from "fs";

const route = process.argv[2] || "/revenue-analytics";
const outName = process.argv[3] || "shot";
const waitMs = Number(process.argv[4] || 3500);
const base = process.env.SHOT_BASE || "http://127.0.0.1:3000";

const outDir = path.resolve(process.cwd(), "../docs/qa_screenshots");
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 2200 } });
const page = await ctx.newPage();
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));

const url = base + route;
await page.goto(url, { waitUntil: "networkidle", timeout: 45000 }).catch((e) => errors.push("GOTO: " + e.message));
await page.waitForTimeout(waitMs);
const outPath = path.join(outDir, outName + ".png");
await page.screenshot({ path: outPath, fullPage: true });
console.log("SAVED", outPath);
console.log("CONSOLE_ERRORS", errors.length);
errors.slice(0, 20).forEach((e) => console.log("  ✗", e));
await browser.close();
