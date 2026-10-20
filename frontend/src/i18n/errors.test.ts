/** Roman Urdu UI gets Roman Urdu wording for known backend errors. */

import { describe, expect, it } from "vitest"
import { localizedError } from "./errors"

describe("localizedError", () => {
  it("keeps the backend sentence in English", () => {
    const message = "Search failed before an answer could be written."
    expect(localizedError(message, "en")).toBe(message)
  })

  it("uses Roman Urdu when that shell language is selected", () => {
    expect(localizedError("Search failed before an answer could be written.", "roman_urdu")).toBe(
      "Talash jawab likhne se pehle fail ho gayi.",
    )
    expect(localizedError("Server error.", "roman_urdu")).toBe("Server ki kharabi.")
    expect(localizedError("The answer took too long.", "roman_urdu")).toBe(
      "Jawab aane mein bahut waqt lag gaya.",
    )
  })
})
