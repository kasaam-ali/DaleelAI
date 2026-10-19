/** Amount validation and network-error copy for the calculator. */

import { describe, expect, it } from "vitest"
import { mapCalcError, wholeRupees } from "./validate"

describe("wholeRupees", () => {
  it("rejects an empty amount", () => {
    expect(wholeRupees("")).toBeNull()
    expect(wholeRupees("   ")).toBeNull()
    expect(wholeRupees(",,,")).toBeNull()
  })

  it("rejects words and negative numbers", () => {
    expect(wholeRupees("abc")).toBeNull()
    expect(wholeRupees("-5000")).toBeNull()
    expect(wholeRupees("12.5")).toBeNull()
  })

  it("accepts zero and comma-grouped rupees", () => {
    expect(wholeRupees("0")).toBe(0)
    expect(wholeRupees("12,000,000")).toBe(12000000)
  })
})

describe("mapCalcError", () => {
  it("turns a failed fetch into a plain message and a retry", () => {
    const mapped = mapCalcError(new TypeError("Failed to fetch"), "Could not reach the tax service.", "Could not calculate.")
    expect(mapped.retry).toBe(true)
    expect(mapped.message).toBe("Could not reach the tax service. (Failed to fetch)")
  })

  it("keeps a service message without offering retry", () => {
    const mapped = mapCalcError(new Error("Enter a whole number."), "Could not reach the tax service.", "Could not calculate.")
    expect(mapped).toEqual({ message: "Enter a whole number.", retry: false })
  })
})
