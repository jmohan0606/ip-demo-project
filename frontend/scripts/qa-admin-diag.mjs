import { chromium } from "playwright";
const LOCAL_API = "http://127.0.0.1:8000";
const b = await chromium.launch();
const p = await (await b.newContext({ viewport: { width: 1440, height: 2000 } })).newPage();
const msgs = [], failed = [];
p.on("console", (m) => msgs.push(`[${m.type()}] ${m.text()}`));
p.on("pageerror", (e) => msgs.push(`[pageerror] ${e.message}`));
p.on("requestfailed", (r) => failed.push(`${r.method()} ${r.url()} :: ${r.failure()?.errorText}`));
p.on("response", (r) => { if (r.status() >= 400) failed.push(`${r.status()} ${r.url()}`); });
await p.route("**/*", async (r) => {
  const u = r.request().url();
  const m = u.match(/^https?:\/\/[^/]*app\.github\.dev(\/.*)$/);
  if (!m) return r.continue();
  const rq = r.request();
  const rs = await fetch(LOCAL_API + m[1], { method: rq.method(), headers: { ...rq.headers(), host: "127.0.0.1:8000", origin: LOCAL_API }, body: ["GET", "HEAD"].includes(rq.method()) ? undefined : rq.postData() ?? undefined });
  return r.fulfill({ status: rs.status, headers: { "content-type": rs.headers.get("content-type") || "application/json", "access-control-allow-origin": "*" }, body: Buffer.from(await rs.arrayBuffer()) });
});
await p.goto("http://127.0.0.1:3000/admin", { waitUntil: "networkidle", timeout: 45000 });
await p.waitForTimeout(2500);
for (const tab of ["System Health", "Model Registry", "Model Strategy", "AI Protections", "Evaluation & Trust", "Observability"]) {
  await p.getByRole("button", { name: tab }).first().click().catch((e) => msgs.push(`[clickfail ${tab}] ${e.message}`));
  await p.waitForTimeout(1800);
}
// Next.js error overlay?
const overlay = await p.locator("nextjs-portal, [data-nextjs-dialog], #__next-build-watcher").count().catch(() => 0);
console.log("=== CONSOLE (non-info) ===");
msgs.filter((m) => !m.startsWith("[log]") && !m.startsWith("[info]") && !m.startsWith("[debug]")).forEach((m) => console.log(" ", m));
console.log("=== FAILED REQUESTS (only app API) ===");
[...new Set(failed)].filter((f) => f.includes("app.github.dev") || f.includes("8000") || /\b(admin|observability|architecture|adapters|evaluation|models)\b/.test(f)).forEach((f) => console.log(" ", f));
console.log("=== overlay count:", overlay);
await b.close();
