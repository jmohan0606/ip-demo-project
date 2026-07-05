import { chromium } from "playwright";
import path from "path"; import fs from "fs";
const base="http://127.0.0.1:3000";
const outDir=path.resolve(process.cwd(),"../docs/qa_screenshots"); fs.mkdirSync(outDir,{recursive:true});
const b=await chromium.launch(); const p=await b.newContext({viewport:{width:1440,height:1700}}).then(c=>c.newPage());
const errs=[]; p.on("console",m=>m.type()==="error"&&errs.push(m.text())); p.on("pageerror",e=>errs.push("PE:"+e.message));
await p.goto(base+"/features-embeddings",{waitUntil:"networkidle",timeout:45000}); await p.waitForTimeout(3500);
// click a feature row (revenue_ltm) to trigger the lineage diagram
await p.getByText("revenue_ltm",{exact:true}).first().click().catch(()=>{});
await p.waitForTimeout(1500);
await p.screenshot({path:path.join(outDir,"featurelab-after.png"),fullPage:true});
console.log("ERRORS",errs.length); errs.slice(0,8).forEach(e=>console.log("  ✗",e));
await b.close();
