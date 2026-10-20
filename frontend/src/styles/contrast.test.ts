/** Port of daleel-proto premium/tokens.py: every Option 2 token pair meets its WCAG threshold. */

import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const css = readFileSync(join(__dirname, "tokens.css"), "utf8")

function block(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`)
  const body = css.slice(start, css.indexOf("}", start))
  const out: Record<string, string> = {}
  for (const match of body.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-f]{6})\s*;/gi)) out[match[1]] = match[2].toLowerCase()
  return out
}

const light = block(":root")
const dark = { ...light, ...block('[data-theme="dark"]') }

function luminance(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const [r, g, b] = c.map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

// [fg, bg, minimum, label] — the 23 pairs from tokens.py, plus --on-strong on solid destructive fills.
const PAIRS: [string, string, number, string][] = [
  ["ink", "paper", 4.5, "Body text on page"],
  ["ink", "field", 4.5, "Body text on card"],
  ["muted", "paper", 4.5, "Secondary text on page"],
  ["muted", "field", 4.5, "Secondary text on card"],
  ["muted", "elevated", 4.5, "Secondary on raised"],
  ["placeholder", "field", 4.5, "Input placeholder"],
  ["seal-ink", "seal", 4.5, "Primary button label"],
  ["seal", "field", 3, "Action colour as UI/icon on card"],
  ["link", "field", 4.5, "Link text"],
  ["brand-ink", "brand", 4.5, "Hero text"],
  ["hero-muted", "brand", 4.5, "Hero sub-text"],
  ["verified", "verified-soft", 4.5, "Verified badge"],
  ["verified", "field", 4.5, "Verified text on card"],
  ["warn", "warn-soft", 4.5, "Warning / example badge"],
  ["refusal", "refusal-soft", 4.5, "Refusal badge"],
  ["refusal", "field", 4.5, "Refusal text on card"],
  ["error", "error-soft", 4.5, "Error badge"],
  ["error", "field", 4.5, "Error text on card"],
  ["web", "field", 4.5, "Gold-tone text"],
  ["rule-strong", "field", 3, "Input border / focus (non-text)"],
  ["nav-ink", "sidebar", 4.5, "Sidebar text"],
  ["nav-muted", "sidebar", 4.5, "Sidebar secondary"],
  ["nav-on", "nav-on-bg", 4.5, "Sidebar active item"],
  ["on-strong", "error", 4.5, "Text on solid destructive fill"],
]

describe.each([
  ["light", light],
  ["dark", dark],
] as const)("Emerald Ledger contrast (%s)", (_mode, tokens) => {
  it.each(PAIRS)("%s on %s ≥ %s:1 (%s)", (fg, bg, min) => {
    expect(tokens[fg], fg).toMatch(/^#[0-9a-f]{6}$/)
    expect(tokens[bg], bg).toMatch(/^#[0-9a-f]{6}$/)
    expect(ratio(tokens[fg], tokens[bg])).toBeGreaterThanOrEqual(min)
  })
})

describe("spec values", () => {
  it("matches §8A for the anchor tokens", () => {
    expect(light.brand).toBe("#0a3d2c")
    expect(light["brand-2"]).toBe("#0a2a5c")
    expect(light.seal).toBe("#0d6b47")
    expect(dark.seal).toBe("#3cc48a")
    expect(light["on-strong"]).toBe("#ffffff")
    expect(dark["on-strong"]).toBe("#140806")
  })

  it("keeps only the allowed radii in the stylesheets", () => {
    const index = readFileSync(join(__dirname, "..", "index.css"), "utf8")
    for (const sheet of [css, index]) {
      for (const match of sheet.matchAll(/border-radius:\s*([^;]+);/g)) {
        expect(match[1]).toMatch(/^var\(--r-(xs|sm|md|lg|xl|full)\)$/)
      }
    }
    expect(css).toContain("--r-xs: 6px")
    expect(css).toContain("--r-xl: 24px")
    expect(css).toContain("--r-full: 9999px")
    expect(index).toContain("--radius-full: var(--r-full)")
  })

  it("uses the §8 spacing scale 4/8/12/16/20/24/32/48", () => {
    const scale = [...css.matchAll(/--space-(\d): (\d+)px/g)].map((m) => [Number(m[1]), Number(m[2])])
    expect(scale).toEqual([[1, 4], [2, 8], [3, 12], [4, 16], [5, 20], [6, 24], [7, 32], [8, 48]])
  })
})
