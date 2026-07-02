import fs from "fs";
const files=[
"components/agp/agp-workspace.tsx",
"app/(dashboard)/agp/page.tsx",
"lib/types/agp.ts"
];
for(const f of files){ if(!fs.existsSync(f)){ process.exit(1);} }
console.log("AGP validation passed");
