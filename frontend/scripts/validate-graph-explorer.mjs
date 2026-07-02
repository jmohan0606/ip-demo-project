import fs from "fs";
const files = [
  "components/graph-explorer/graph-explorer-workspace.tsx",
  "components/graph-explorer/graph-node-card.tsx",
  "app/(dashboard)/graph-explorer/page.tsx",
  "lib/api/graph_explorer.ts",
  "lib/types/graph_explorer.ts"
];
for (const f of files) {
  if (!fs.existsSync(f)) {
    console.error(`Missing ${f}`);
    process.exit(1);
  }
}
const page = fs.readFileSync("components/graph-explorer/graph-explorer-workspace.tsx", "utf8");
for (const term of ["Graph Canvas", "Node Details", "Explainability Paths", "Traversal Use Cases"]) {
  if (!page.includes(term)) {
    console.error(`Missing ${term}`);
    process.exit(1);
  }
}
console.log("Graph explorer validation passed");
