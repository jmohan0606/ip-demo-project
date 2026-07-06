// Internal QA screenshot: rewrites browser-side API calls from the public
// Codespaces URL (which needs the human's browser auth) to the local backend, so
// screenshots taken *inside* the container render real data without CORS/auth.
// The committed .env.local keeps the public URL for the real external browser.
// Usage: node scripts/qa-shot.mjs <route> <outName> [waitMs]
import { chromium } from "playwright";
import path from "path";
import fs from "fs";

const route = process.argv[2] || "/dashboard";
const outName = process.argv[3] || "qa-shot";
const waitMs = Number(process.argv[4] || 5000);
const LOCAL_API = "http://127.0.0.1:8000";

const outDir = path.resolve(process.cwd(), "../docs/qa_screenshots");
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 2400 } });
const page = await ctx.newPage();
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));

// Proxy any request to a *.app.github.dev host to the local http backend
// (Playwright forbids changing protocol via continue(), so fulfill manually).
await page.route("**/*", async (r) => {
  const u = r.request().url();
  const m = u.match(/^https?:\/\/[^/]*app\.github\.dev(\/.*)$/);
  if (!m) return r.continue();
  const req = r.request();
  try {
    const resp = await fetch(LOCAL_API + m[1], {
      method: req.method(),
      headers: { ...req.headers(), host: "127.0.0.1:8000", origin: LOCAL_API },
      body: ["GET", "HEAD"].includes(req.method()) ? undefined : req.postData() ?? undefined,
    });
    const body = Buffer.from(await resp.arrayBuffer());
    return r.fulfill({
      status: resp.status,
      headers: { "content-type": resp.headers.get("content-type") || "application/json", "access-control-allow-origin": "*" },
      body,
    });
  } catch (e) {
    return r.fulfill({ status: 502, contentType: "application/json", body: JSON.stringify({ error: String(e) }) });
  }
});

await page.goto("http://127.0.0.1:3000" + route, { waitUntil: "networkidle", timeout: 45000 }).catch((e) => errors.push("GOTO: " + e.message));
await page.waitForTimeout(waitMs);
await page.screenshot({ path: path.join(outDir, outName + ".png"), fullPage: true });
console.log("SAVED", path.join(outDir, outName + ".png"));
console.log("CONSOLE_ERRORS", errors.length);
errors.slice(0, 20).forEach((e) => console.log("  x", e));
await browser.close();
