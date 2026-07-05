// Interactive scope-following verification for Revenue Analytics.
// Loads Firm, drills into a Division via the breadcrumb drill dropdown, changes period,
// and reports the Total Revenue KPI + geography at each step to prove data re-scopes.
import { chromium } from "playwright";
import path from "path";
import fs from "fs";

const base = process.env.SHOT_BASE || "http://127.0.0.1:3000";
const outDir = path.resolve(process.cwd(), "../docs/qa_screenshots");
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newContext({ viewport: { width: 1440, height: 2200 } }).then((c) => c.newPage());
const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));

async function readState(tag) {
  await page.waitForTimeout(2500);
  // KPI total revenue is the first big value; grab all text and pull the numbers we show.
  const total = await page.locator("text=Total Revenue").first().locator("xpath=../..").innerText().catch(() => "n/a");
  const heading = await page.locator("h2").first().innerText().catch(() => "n/a");
  const states = await page.locator("text=/\\d+ states/").first().innerText().catch(() => "n/a");
  console.log(`\n[${tag}] heading="${heading.replace(/\n/g, " ")}"`);
  console.log(`   ${total.replace(/\n/g, " ")}`);
  console.log(`   geo=${states}`);
  return heading + total;
}

await page.goto(base + "/revenue-analytics", { waitUntil: "networkidle", timeout: 45000 });
const firm = await readState("FIRM default");

// Drill into a Division via the dashed "Drill into Division…" dropdown.
const drill = page.locator('select:has-text("Drill into")').first();
const opts = await drill.locator("option").allTextContents();
console.log("\ndrill options:", opts.join(" | "));
// pick Central Division if present, else the 2nd option
await drill.selectOption({ label: opts.find((o) => /Central/.test(o)) || opts[1] });
const div = await readState("DIVISION drilled");

// Change period to ALL via the Period dropdown.
const period = page.locator("select").filter({ hasText: "YTD" }).first();
await period.selectOption({ label: "ALL" }).catch(async () => {
  // period options may be value-based; try value
  await period.selectOption("ALL").catch(() => {});
});
const allp = await readState("DIVISION period=ALL");

await page.screenshot({ path: path.join(outDir, "revenue-after-division.png"), fullPage: true });
console.log("\nSAVED", path.join(outDir, "revenue-after-division.png"));
console.log("CONSOLE_ERRORS", errors.length);
errors.slice(0, 10).forEach((e) => console.log("  ✗", e));
console.log("\nSCOPE-FOLLOWING:", firm !== div ? "PASS (firm != division)" : "FAIL (identical)");
await browser.close();
