// Click a button by text, then screenshot. Usage: node scripts/qa-click.mjs <route> <buttonText> <outName> [waitMs]
import { chromium } from "playwright";
import path from "path";
import fs from "fs";
const [route, btnText, outName, waitMs = "3000"] = process.argv.slice(2);
const LOCAL_API = "http://127.0.0.1:8000";
const outDir = path.resolve(process.cwd(), "../docs/qa_screenshots");
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1440, height: 2400 } })).newPage();
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
await page.getByRole("button", { name: btnText }).first().click().catch((e) => errors.push("click: " + e.message));
await page.waitForTimeout(Number(waitMs));
await page.screenshot({ path: path.join(outDir, outName + ".png"), fullPage: true });
console.log("SAVED", outName, "ERRORS", errors.length);
errors.slice(0, 8).forEach((e) => console.log("  x", e));
await browser.close();
