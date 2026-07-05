import { chromium } from "playwright";
import path from "path"; import fs from "fs";
const base = "http://127.0.0.1:3000";
const outDir = path.resolve(process.cwd(), "../docs/qa_screenshots"); fs.mkdirSync(outDir,{recursive:true});
const b = await chromium.launch(); const p = await b.newContext({viewport:{width:1440,height:1600}}).then(c=>c.newPage());
const errs=[]; p.on("console",m=>m.type()==="error"&&errs.push(m.text())); p.on("pageerror",e=>errs.push("PE:"+e.message));
await p.goto(base+"/what-if",{waitUntil:"networkidle",timeout:45000}); await p.waitForTimeout(2500);
// click Run Scenario
await p.getByText("Run Scenario").click().catch(()=>{});
await p.waitForTimeout(2500);
// click Save
await p.getByRole("button",{name:/^Save$/}).click().catch(async()=>{ await p.getByText("Save",{exact:true}).click().catch(()=>{}); });
await p.waitForTimeout(2500);
await p.screenshot({path:path.join(outDir,"whatif-after.png"),fullPage:true});
const savedTxt = await p.locator("text=/Saved rec_whatif|through the recommendations pipeline/").first().innerText().catch(()=>"(no save confirmation captured)");
console.log("SAVE CONFIRMATION:", savedTxt.replace(/\n/g," ").slice(0,160));
console.log("ERRORS", errs.length); errs.slice(0,8).forEach(e=>console.log("  ✗",e));
await b.close();
