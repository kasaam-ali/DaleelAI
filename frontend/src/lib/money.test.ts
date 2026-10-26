/** Checks rupee grouping and the lakh or crore hint. */

import { describe, expect, it } from "vitest"
import { annotatePkr, formatPkr } from "./money"

describe("formatPkr", () => {
  it("writes the spec example", () => {
    expect(formatPkr(1_800_000)).toBe("Rs 1,800,000 (18 lakh)")
  })

  it("uses crore from one crore up", () => {
    expect(formatPkr(25_000_000)).toBe("Rs 25,000,000 (2.5 crore)")
    expect(formatPkr(10_000_000)).toBe("Rs 10,000,000 (1 crore)")
  })

  it("skips the hint under one lakh", () => {
    expect(formatPkr(50_000)).toBe("Rs 50,000")
  })
})

describe("annotatePkr", () => {
  it("adds a hint without rewriting the digits", () => {
    expect(annotatePkr("Pay Rs 1800000 this year.")).toBe("Pay Rs 1800000 (18 lakh) this year.")
  })

  it("does not add a second hint", () => {
    expect(annotatePkr("Rs 1,800,000 (18 lakh)")).toBe("Rs 1,800,000 (18 lakh)")
  })

  it("leaves an unlabeled amount for the redactor's sake", () => {
    expect(annotatePkr("25000000")).toBe("25000000")
  })
})
