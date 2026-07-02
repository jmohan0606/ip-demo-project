import fs from "fs";
const files = [
  "components/advisor360/advisor360-client.tsx",
  "app/(dashboard)/advisor-360/page.tsx",
  "lib/api/advisor360.ts",
  "lib/types/advisor360.ts"
];
for (const f of files) {
  if (!fs.existsSync(f)) {
    console.error(`Missing ${f}`);
    process.exit(1);
  }
}
const page = fs.readFileSync("components/advisor360/advisor360-client.tsx", "utf8");
for (const term of ["Household Intelligence", "CRM Activity Timeline", "Accounts", "Transaction Detail", "Next Best Action"]) {
  if (!page.includes(term)) {
    console.error(`Missing term ${term}`);
    process.exit(1);
  }
}
console.log("Advisor 360 validation passed");
