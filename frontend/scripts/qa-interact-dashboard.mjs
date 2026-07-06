// Prove the Executive Dashboard re-rolls on scope + period change (12.1 evidence).
import { chromium } from "playwright";
import path from "path";
import fs from "fs";

const LOCAL_API = "http://127.0.0.1:8000";
const outDir = path.resolve(process.cwd(), "../docs/qa_screenshots");
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 2400 } });
const page = await ctx.newPage();
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.route("**/*", async (r) => {
  const u = r.request().url();
  const m = u.match(/^https?:\/\/[^/]*app\.github\.dev(\/.*)$/);
  if (!m) return r.continue();
  const req = r.request();
  const resp = await fetch(LOCAL_API + m[1], {
    method: req.method(),
    headers: { ...req.headers(), host: "127.0.0.1:8000", origin: LOCAL_API },
    body: ["GET", "HEAD"].includes(req.method()) ? undefined : req.postData() ?? undefined,
  });
  return r.fulfill({ status: resp.status, headers: { "content-type": resp.headers.get("content-type") || "application/json", "access-control-allow-origin": "*" }, body: Buffer.from(await resp.arrayBuffer()) });
});

await page.goto("http://127.0.0.1:3000/dashboard", { waitUntil: "networkidle", timeout: 45000 });
await page.waitForTimeout(3500);

// Read the firm headline revenue text.
const firmTitle = await page.locator("h2").first().innerText().catch(() => "?");

// Drill into a division via the dashed "Drill into Division…" select in the breadcrumb.
const drill = page.locator("select").filter({ hasText: "Drill into" }).first();
await drill.selectOption({ index: 1 }).catch((e) => errors.push("drill: " + e.message));
await page.waitForTimeout(3000);

// Change Period to QTD (the 2nd period select — MTD/QTD/YTD/LTM).
const periodSelect = page.locator("select").filter({ hasText: "YTD" }).first();
await periodSelect.selectOption("QTD").catch((e) => errors.push("period: " + e.message));
await page.waitForTimeout(3500);

const divTitle = await page.locator("h2").first().innerText().catch(() => "?");
await page.screenshot({ path: path.join(outDir, "s12-1-dashboard-division-qtd.png"), fullPage: true });
console.log("FIRM TITLE:", firmTitle);
console.log("DIVISION TITLE:", divTitle);
console.log("CONSOLE_ERRORS", errors.length);
errors.slice(0, 10).forEach((e) => console.log("  x", e));
await browser.close();
