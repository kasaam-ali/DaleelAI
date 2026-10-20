/** Disabled buttons (e.g. Send on an empty composer) show not-allowed, not the global pointer. */

import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

const css = readFileSync(new URL("../index.css", import.meta.url), "utf8")

describe("disabled cursor", () => {
  it("an unlayered not-allowed rule for disabled buttons comes after the unlayered pointer rule", () => {
    const pointer = css.search(/button,\s*select,\s*a\s*\{\s*cursor:\s*pointer;/)
    const disabled = css.search(/button:disabled,\s*button\[aria-disabled="true"\]\s*\{\s*cursor:\s*not-allowed;/)
    expect(pointer).toBeGreaterThan(-1)
    expect(disabled).toBeGreaterThan(pointer)
    // Not inside an @layer block (a layered rule would lose to the unlayered pointer rule).
    const before = css.slice(0, disabled)
    const opens = (before.match(/@layer[^;{]*\{/g) ?? []).length
    expect(opens === 0 || before.lastIndexOf("}") > before.lastIndexOf("@layer")).toBe(true)
  })
})
