import { chromium } from "playwright";
import { mkdirSync } from "fs";

const OUT = process.argv[2] || "../docs/qa_screenshots/session11";
mkdirSync(OUT, { recursive: true });
const pages = process.argv.slice(3);

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1600 } });
const page = await ctx.newPage();
for (const spec of pages) {
  const [name, url] = spec.split("|");
  try {
    await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
    await page.waitForTimeout(3500);
    await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
    console.log("shot", name);
  } catch (e) {
    console.log("FAIL", name, String(e).slice(0, 120));
  }
}
await browser.close();
