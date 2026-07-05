import { chromium } from "playwright";
import path from "path"; import fs from "fs";
const outDir=path.resolve(process.cwd(),"../docs/qa_screenshots"); fs.mkdirSync(outDir,{recursive:true});
const b=await chromium.launch(); const p=await b.newContext({viewport:{width:1440,height:900}}).then(c=>c.newPage());
const errs=[]; p.on("console",m=>m.type()==="error"&&errs.push(m.text())); p.on("pageerror",e=>errs.push("PE:"+e.message));
await p.goto("http://127.0.0.1:3000/revenue-analytics",{waitUntil:"networkidle",timeout:45000}); await p.waitForTimeout(3000);
// scroll the trend explorer into view so its Recharts measures correctly
const el = p.getByText("Revenue Trend Explorer").first();
await el.scrollIntoViewIfNeeded().catch(()=>{});
await p.waitForTimeout(1500);
// switch to Monthly to force a re-render while in view
await p.getByRole("button",{name:"Monthly"}).click().catch(()=>{});
await p.waitForTimeout(1800);
// screenshot just the explorer card region
const box = await el.locator("xpath=ancestor::div[contains(@class,'rounded')][1]").boundingBox().catch(()=>null);
await p.screenshot({path:path.join(outDir,"trend-explorer-focus.png"), clip: box ? {x:box.x,y:Math.max(0,box.y),width:box.width,height:Math.min(1400,box.height)} : undefined, fullPage: !box});
console.log("ERRORS",errs.length); errs.slice(0,6).forEach(e=>console.log("  ✗",e));
await b.close();
