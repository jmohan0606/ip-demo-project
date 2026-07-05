import { chromium } from "playwright";
import path from "path"; import fs from "fs";
const route=process.argv[2], out=process.argv[3], sendSel=process.argv[4]||"Send";
const base="http://127.0.0.1:3000";
const outDir=path.resolve(process.cwd(),"../docs/qa_screenshots"); fs.mkdirSync(outDir,{recursive:true});
const b=await chromium.launch(); const p=await b.newContext({viewport:{width:1440,height:1800}}).then(c=>c.newPage());
const errs=[]; p.on("console",m=>m.type()==="error"&&errs.push(m.text())); p.on("pageerror",e=>errs.push("PE:"+e.message));
await p.goto(base+route,{waitUntil:"networkidle",timeout:45000}); await p.waitForTimeout(2500);
// click first suggestion chip to trigger a real answer
await p.locator("button", {hasText: /Why|What|How|When|Explain|referrals|threshold/}).first().click().catch(()=>{});
await p.waitForTimeout(4500);
await p.screenshot({path:path.join(outDir,out+".png"),fullPage:true});
console.log("SAVED",out,"ERRORS",errs.length); errs.slice(0,8).forEach(e=>console.log("  ✗",e));
await b.close();
