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
    expect(t("roman_urdu", "navHome")).toBe("Home")
    expect(t("roman_urdu", "groupTax")).toBe("Tax ke zariye")
    expect(t("roman_urdu", "calcTitle")).toBe("Wifaqi tax calculator")
    expect(t("roman_urdu", "becomeFiler")).toBe("Filer banein (infiradi NTN)")
    expect(t("en", "stepUnderstand")).toBe("Question understood")
    expect(t("en", "stepLibrary")).toBe("Searching the library…")
    expect(t("en", "stepWrite")).toBe("Writing the answer")
    expect(t("en", "stepCheck")).toBe("Checking citations")
    expect(t("en", "answerFailedTitle")).toBe("The answer didn't arrive")
    expect(t("roman_urdu", "stepCheck")).toBe("Hawalay check kar raha hoon")
    expect(t("roman_urdu", "answerFailedTitle")).toBe("Jawab nahi aa saka")
    expect(t("roman_urdu", "searchFailed")).toBe("Talash jawab likhne se pehle fail ho gayi.")
    // Prototype copy (premium-home.html, shared.js) is identical in both languages for these keys.
    const prototypeSame = ["requestId", "fbrLawsDetail", "navTools", "navAsk", "navCalcTool", "navNoticeTool", "railHome", "railNotice", "railAbout", "themeToggle", "taxYearLabel", "fsOptional", "fsFiler", "fsFilerOpt", "fsNonFilerOpt", "heroEyebrow", "heroChip1", "heroChip2", "heroChip3", "toolsLabel", "tool2Title", "tool2Meta", "tool3Title", "artQuestion", "navHome", "subtitle", "profileTitle", "dataClearWhat1", "nvChecklists", "nvListsShort", "chatsNav"]
    const keep = new Set(["product", "romanUrdu", "helplineDetail", ...prototypeSame])
    const copied = Object.keys(en).filter((key) => en[key] === romanUrdu[key] && !keep.has(key))
    expect(copied).toEqual([])
    expect("urdu" in en).toBe(false)
  })
})
