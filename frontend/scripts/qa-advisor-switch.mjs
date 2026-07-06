// Prove the explicit AdvisorSelector re-scopes a page's data (12.6).
import { chromium } from "playwright";
import path from "path";
import fs from "fs";
const [route, outPrefix] = process.argv.slice(2);
const LOCAL_API = "http://127.0.0.1:8000";
const outDir = path.resolve(process.cwd(), "../docs/qa_screenshots");
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1440, height: 2200 } })).newPage();
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.route("**/*", async (r) => {
  const u = r.request().url();
  const m = u.match(/^https?:\/\/[^/]*app\.github\.dev(\/.*)$/);
  if (!m) return r.continue();
  const req = r.request();
  const resp = await fetch(LOCAL_API + m[1], { method: req.method(), headers: { ...req.headers(), host: "127.0.0.1:8000", origin: LOCAL_API }, body: ["GET", "HEAD"].includes(req.method()) ? undefined : req.postData() ?? undefined });
  return r.fulfill({ status: resp.status, headers: { "content-type": resp.headers.get("content-type") || "application/json", "access-control-allow-origin": "*" }, body: Buffer.from(await resp.arrayBuffer()) });
});
await page.goto("http://127.0.0.1:3000" + route, { waitUntil: "networkidle", timeout: 45000 });
await page.waitForTimeout(4000);
const before = await page.locator("p").first().innerText().catch(() => "?");
await page.screenshot({ path: path.join(outDir, outPrefix + "-a.png"), fullPage: true });
// The AdvisorSelector is the select with primary styling; pick by its title.
const sel = page.locator('select[title*="Select an advisor"]').first();
const opts = await sel.locator("option").all();
// choose an option far down the list (a different advisor)
const targetVal = await opts[Math.min(19, opts.length - 1)].getAttribute("value");
await sel.selectOption(targetVal).catch((e) => errors.push("select: " + e.message));
await page.waitForTimeout(4500);
const after = await page.locator("p").first().innerText().catch(() => "?");
await page.screenshot({ path: path.join(outDir, outPrefix + "-b.png"), fullPage: true });
console.log("BEFORE:", before.slice(0, 90));
console.log("AFTER :", after.slice(0, 90));
console.log("SWITCHED TO:", targetVal, "ERRORS", errors.length);
errors.slice(0, 6).forEach((e) => console.log("  x", e));
await browser.close();
