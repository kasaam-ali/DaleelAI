/** Non-JSON failures ("Request failed (500)") follow the shell language too. */

import { describe, expect, it } from "vitest"
import { localizedError } from "./errors"

describe("localizedError request failed", () => {
  it("translates a non-JSON status failure in Roman Urdu", () => {
    expect(localizedError("Request failed (500)", "roman_urdu")).toBe("Request nakam ho gayi (500)")
    expect(localizedError("Request failed (502)", "en")).toBe("Request failed (502)")
  })
})
