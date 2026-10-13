import { readFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"
import { redactPii } from "./pii"

const casesPath = resolve(dirname(fileURLToPath(import.meta.url)), "../../../contracts/pii_cases.json")
const cases = JSON.parse(readFileSync(casesPath, "utf8")) as {
  cases: { id: string; input: string; output: string }[]
}

describe("redactPii", () => {
  for (const item of cases.cases) {
    it(item.id, () => {
      expect(redactPii(item.input)).toBe(item.output)
    })
  }

  it("leaves a redacted string unchanged", () => {
    const once = redactPii(cases.cases.map((item) => item.input).join("\n"))
    expect(redactPii(once)).toBe(once)
  })
})
