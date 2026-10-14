import { describe, expect, it } from "vitest"
import { widthPercent } from "./bars"

describe("widthPercent", () => {
  it("scales the larger amount to the full bar", () => {
    expect(widthPercent(200, 50)).toBe(100)
    expect(widthPercent(50, 200)).toBe(25)
  })

  it("fills both bars when the amounts match", () => {
    expect(widthPercent(10, 10)).toBe(100)
  })
})