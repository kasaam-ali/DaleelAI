/** Runs the frontend unit tests. */

import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { defineConfig } from "vitest/config"
import { fbrLawDate } from "./src/lib/lawDate.ts"

const catalog = readFileSync(fileURLToPath(new URL("../backend/pipeline/catalog.csv", import.meta.url)), "utf8")

export default defineConfig({
  define: {
    __FBR_LAW_DATE__: JSON.stringify(fbrLawDate(catalog)),
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
})
