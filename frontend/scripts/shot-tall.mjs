import { chromium } from "playwright";
import path from "path"; import fs from "fs";
const outDir=path.resolve(process.cwd(),"../docs/qa_screenshots"); fs.mkdirSync(outDir,{recursive:true});
const b=await chromium.launch(); const p=await b.newContext({viewport:{width:1440,height:3200}}).then(c=>c.newPage());
const errs=[]; p.on("console",m=>m.type()==="error"&&errs.push(m.text()));
await p.goto("http://127.0.0.1:3000/revenue-analytics",{waitUntil:"networkidle",timeout:45000});
await p.waitForTimeout(5000); // let all in-view ResponsiveContainers measure + animate
await p.screenshot({path:path.join(outDir,"revenue-trend-explorer.png"), fullPage:true});
console.log("ERRORS",errs.length);
await b.close();
