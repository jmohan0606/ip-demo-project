import { chromium } from "playwright";
import path from "path"; import fs from "fs";
const adv = process.argv[2] || "A025"; const out = process.argv[3] || "advisor360-"+adv;
const base = "http://127.0.0.1:3000";
const outDir = path.resolve(process.cwd(), "../docs/qa_screenshots"); fs.mkdirSync(outDir,{recursive:true});
const b = await chromium.launch(); const p = await b.newContext({viewport:{width:1440,height:2322}}).then(c=>c.newPage());
const errs=[]; p.on("console",m=>m.type()==="error"&&errs.push(m.text())); p.on("pageerror",e=>errs.push("PE:"+e.message));
await p.goto(base+"/advisor-360",{waitUntil:"networkidle",timeout:45000}); await p.waitForTimeout(3000);
// select advisor in the top-right advisor dropdown (the one whose options include " — ")
const sel = p.locator("select").filter({hasText:"—"}).first();
await sel.selectOption(adv).catch(async()=>{ await sel.selectOption({label:new RegExp(adv)}).catch(()=>{}); });
await p.waitForTimeout(4000);
const h1 = await p.locator("h1").first().innerText();
const agp = await p.locator("text=AGP Status").first().locator("xpath=../..").innerText().catch(()=>"n/a");
console.log("H1:", h1.replace(/\n/g," "));
console.log("AGP card:", agp.replace(/\n/g," ").slice(0,160));
await p.screenshot({path:path.join(outDir,out+".png"),fullPage:true});
console.log("SAVED",out,"ERRORS",errs.length); errs.slice(0,8).forEach(e=>console.log(" ✗",e));
await b.close();
