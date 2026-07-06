import { chromium } from "playwright";
import path from "path"; import fs from "fs";
const LOCAL_API = "http://127.0.0.1:8000";
const outDir = path.resolve(process.cwd(), "../docs/qa_screenshots/section13B");
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1440, height: 1400 } })).newPage();
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.route("**/*", async (r) => {
  const u = r.request().url();
  const m = u.match(/^https?:\/\/[^/]*app\.github\.dev(\/.*)$/);
  if (!m) return r.continue();
  const rq = r.request();
  const rs = await fetch(LOCAL_API + m[1], { method: rq.method(), headers: { ...rq.headers(), host: "127.0.0.1:8000", origin: LOCAL_API }, body: ["GET", "HEAD"].includes(rq.method()) ? undefined : rq.postData() ?? undefined });
  return r.fulfill({ status: rs.status, headers: { "content-type": rs.headers.get("content-type") || "application/json", "access-control-allow-origin": "*" }, body: Buffer.from(await rs.arrayBuffer()) });
});
const shot = (n) => page.screenshot({ path: path.join(outDir, n + ".png"), fullPage: false });

await page.goto("http://127.0.0.1:3000/story", { waitUntil: "networkidle", timeout: 45000 });
await page.waitForTimeout(3000);
await page.getByRole("button", { name: /Start — Advisor Journey/ }).click();
await page.waitForTimeout(6000);           // reset + baseline capture + step 1 nav
await shot("s13b-step01-trigger");
// advance to the action step (steps 2..5)
for (let i = 0; i < 4; i++) { await page.getByRole("button", { name: /^Next/ }).click().catch(() => {}); await page.waitForTimeout(3500); }
await shot("s13b-step05-action");
// run the real accept+complete action
await page.getByRole("button", { name: /Accept & Complete/ }).click().catch((e) => errors.push("action: " + e.message));
await page.waitForTimeout(4000);
await shot("s13b-step05-after-action");
// advance to impact + propagation steps
await page.getByRole("button", { name: /^Next/ }).click().catch(() => {}); await page.waitForTimeout(4000); await shot("s13b-step06-impact");
await page.getByRole("button", { name: /^Next/ }).click().catch(() => {}); await page.waitForTimeout(4500); await shot("s13b-step07-prop-revenue");
await page.getByRole("button", { name: /^Next/ }).click().catch(() => {}); await page.waitForTimeout(4500); await shot("s13b-step08-prop-firm");
console.log("SHOTS DONE · console errors:", errors.length);
errors.slice(0, 8).forEach((e) => console.log("  x", e));
await browser.close();
