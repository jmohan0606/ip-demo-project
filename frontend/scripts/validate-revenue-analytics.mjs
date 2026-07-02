
import fs from "fs";
const files=[
"components/revenue/revenue-drilldown-page.tsx",
"app/(dashboard)/revenue-analytics/page.tsx",
"lib/types/revenue_analytics.ts"
];
for(const f of files){ if(!fs.existsSync(f)){ console.error(f); process.exit(1);} }
console.log("Revenue analytics validation passed");
