import { chromium } from "playwright";
const LOCAL_API="http://127.0.0.1:8000";
const b=await chromium.launch(); const p=await(await b.newContext()).newPage();
await p.route("**/*",async r=>{const u=r.request().url();const m=u.match(/^https?:\/\/[^/]*app\.github\.dev(\/.*)$/);if(!m)return r.continue();const rq=r.request();const rs=await fetch(LOCAL_API+m[1],{method:rq.method(),headers:{...rq.headers(),host:"127.0.0.1:8000",origin:LOCAL_API}});return r.fulfill({status:rs.status,headers:{"content-type":rs.headers.get("content-type")||"application/json","access-control-allow-origin":"*"},body:Buffer.from(await rs.arrayBuffer())})});
await p.goto("http://127.0.0.1:3000/admin",{waitUntil:"networkidle"});
await p.waitForTimeout(2000);
const portalText = await p.locator("nextjs-portal").innerText().catch(()=>"(no nextjs-portal text)");
console.log("PORTAL TEXT:", portalText.slice(0,300) || "(empty)");
await b.close();
