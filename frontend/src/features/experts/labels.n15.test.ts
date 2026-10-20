/** N11/N12: checklist title follows the shell; category chips show human labels. */

import { describe, expect, it } from "vitest"
import { t, type CopyKey } from "../../i18n"
import { checklistTitle } from "../checklists/ChecklistsPage"
import { categoryLabel } from "./ExpertsPage"

describe("N11 checklist title", () => {
  const saved = { id: "1", template_id: "t", title: "Start", title_en: "Start", title_ru: "Shuru", steps: [], progress: 0 }
  it("switches with the shell language", () => {
    expect(checklistTitle(saved, "roman_urdu")).toBe("Shuru")
    expect(checklistTitle(saved, "en")).toBe("Start")
  })
})

describe("N12 category labels", () => {
  it("never shows raw keys", () => {
    for (const language of ["en", "roman_urdu"] as const) {
      const copy = (key: CopyKey) => t(language, key)
      expect(categoryLabel("income_tax", copy)).toContain("Income tax")
      expect(categoryLabel("audit_notice", copy)).not.toContain("_")
    }
  })
})
