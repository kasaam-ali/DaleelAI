/** English and Roman Urdu stay in parity, and Urdu script is not a UI language. */

import { describe, expect, it } from "vitest"
import { t } from "./index"
import en from "./en.json" with { type: "json" }
import romanUrdu from "./roman_urdu.json" with { type: "json" }

describe("copy", () => {
  it("gives Roman Urdu its own shell strings", () => {
    expect(Object.keys(romanUrdu).sort()).toEqual(Object.keys(en).sort())
    expect(t("roman_urdu", "homeTitle")).not.toBe(t("en", "homeTitle"))
    expect(t("en", "romanUrdu")).toBe("Roman Urdu")
    expect(t("roman_urdu", "answerIn")).toBe("Jawab is mein")
    expect("urdu" in en).toBe(false)
  })
})
