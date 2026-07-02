import fs from "node:fs";
import path from "node:path";

const required = [
  "components/layout/shell-context.tsx",
  "components/layout/app-shell.tsx",
  "components/layout/top-header.tsx",
  "components/navigation/sidebar-navigation.tsx",
  "components/navigation/mobile-context-drawer.tsx",
  "components/status/persona-scope-selector.tsx",
  "components/status/active-context-bar.tsx",
  "components/status/runtime-mode-pill.tsx",
  "lib/scope-options.ts",
  "lib/types/shell.ts"
];

const missing = required.filter((file) => !fs.existsSync(path.join(process.cwd(), file)));
if (missing.length) {
  console.error("Missing navigation shell files:");
  for (const file of missing) console.error(`- ${file}`);
  process.exit(1);
}

const shell = fs.readFileSync(path.join(process.cwd(), "components/layout/app-shell.tsx"), "utf8");
const requiredTokens = ["ShellContext.Provider", "persona", "scopeType", "scopeId", "period", "compareTo"];
const missingTokens = requiredTokens.filter((token) => !shell.includes(token));
if (missingTokens.length) {
  console.error("Missing shell state tokens:", missingTokens);
  process.exit(1);
}

console.log("Navigation shell validation passed.");
