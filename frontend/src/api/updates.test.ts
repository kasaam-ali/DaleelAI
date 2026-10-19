/** The updates summary follows the shell language when the API splits it. */

import { describe, expect, it } from "vitest"
import { summaryFor, type UpdateItem } from "./updates"

const item: UpdateItem = {
  id: "1",
  title: "SRO",
  doc_type: "sro",
  domain: "income_tax",
  published_at: "2026-10-01",
  effective_from: null,
  summary: "English half.\n\nRoman Urdu half.",
  summary_en: "English half.",
  summary_ru: "Roman Urdu half.",
  who_is_affected: null,
  key_changes: [],
  source_url: "https://fbr.gov.pk/",
}

describe("summaryFor", () => {
  it("uses the English and Roman Urdu fields", () => {
    expect(summaryFor(item, "en")).toBe("English half.")
    expect(summaryFor(item, "roman_urdu")).toBe("Roman Urdu half.")
  })

  it("splits a combined summary on the first blank line", () => {
    const combined = { ...item, summary_en: undefined, summary_ru: undefined }
    expect(summaryFor(combined, "en")).toBe("English half.")
    expect(summaryFor(combined, "roman_urdu")).toBe("Roman Urdu half.")
  })
})
