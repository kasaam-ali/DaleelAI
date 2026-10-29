/** Ask Daleel composer focus: soft seal outline, no thick 4px box-shadow rectangle. */

import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

const css = readFileSync(new URL("../index.css", import.meta.url), "utf8")

describe("composer focus ring", () => {
  it("uses a soft outline on focus-within instead of a 4px box-shadow ring", () => {
    const block = css.match(/\.composer:focus-within\s*\{[^}]+\}/)
    expect(block).not.toBeNull()
    const body = block![0]
    expect(body).toMatch(/border-color:\s*var\(--seal\)/)
    expect(body).toMatch(/outline:\s*var\(--focus-width\)/)
    expect(body).not.toMatch(/box-shadow:\s*0\s+0\s+0\s+4px/)
  })

  it("suppresses nested focus-visible outlines so the box is not doubled", () => {
    const block = css.match(/\.composer\s+:focus-visible\s*\{[^}]+\}/)
    expect(block).not.toBeNull()
    expect(block![0]).toMatch(/outline:\s*none/)
  })
})
