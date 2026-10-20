/** PR 5b: composer redaction preview, empty Send, masked sent title, and in-chat tool cards. */

// @vitest-environment happy-dom
import { act } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, describe, expect, it } from "vitest"
import { t } from "../../i18n"
import { redactPii, redactWithSpans } from "../../lib/pii"
import AnswerSlip from "./AnswerSlip"
import AnswerTitle from "./answer/AnswerTitle"
import Composer from "./Composer"
import type { Turn } from "./types"

const copy = (key: Parameters<typeof t>[1]) => t("en", key)
let root: Root
let host: HTMLDivElement

function mount(node: React.ReactNode) {
  host = document.createElement("div")
  document.body.append(host)
  root = createRoot(host)
  act(() => root.render(node))
}

afterEach(() => {
  act(() => root?.unmount())
  host?.remove()
})

function toolTurn(type: string, data: Record<string, unknown>, answer: string): Turn {
  return {
    id: "t1", question: "q", redacted: false, status: "", draft: "", sources: [], intent: "tool",
    detectedLanguage: "en", phases: [], queued: false, stopped: false, replyLanguage: "en",
    autoRetryIn: null, autoRetryCancelled: false, sentAt: null, phaseTimes: [null, null, null, null],
    final: { answer, answer_source: "none", confidence: "low", verified: false, model: "none", tax_year: "TY2026",
      corpus_date: "2026-10-14", action_links: [], follow_ups: [], cached: false },
    error: null, messageId: "m1", taxYear: "TY2026", feedback: null, feedbackNote: null, toolNote: false,
    toolCard: { type, data },
  }
}

function slip(turn: Turn) {
  mount(
    <AnswerSlip turn={turn} copy={copy} language="en" activeCite={null} onOpen={() => undefined}
      onFeedback={() => undefined} onAsk={() => undefined} onToast={() => undefined} />,
  )
}

describe("composer guard", () => {
  it("masks in the same order and marks the placeholders", () => {
    const raw = "Mera CNIC 35202-1234567-1 aur NTN 1234567-8 hai"
    const out = redactWithSpans(raw)
    expect(out.text).toBe("Mera CNIC [CNIC] aur [NTN] hai")
    expect(out.text).toBe(redactPii(raw))
    expect(out.parts.filter((part) => part.tag).map((part) => part.text)).toEqual(["[CNIC]", "[NTN]"])
    expect(redactWithSpans("no numbers").changed).toBe(false)
  })

  it("shows [CNIC] in the live preview", () => {
    const value = "My CNIC is 35202-1234567-1"
    mount(<Composer value={value} busy={false} error={null} preview={redactWithSpans(value).parts} copy={copy}
      onChange={() => undefined} onSubmit={() => undefined} onStop={() => undefined} />)
    const preview = host.querySelector(".gprev")
    expect(preview?.textContent).toContain("Personal details will be removed before this is sent.")
    expect(preview?.textContent).toContain("Will be sent as:")
    expect(preview?.querySelector("mark.mk")?.textContent).toBe("[CNIC]")
  })

  it("keeps an empty Send focusable with aria-disabled, and hints on whitespace", () => {
    mount(<Composer value="   " busy={false} error={null} preview={null} copy={copy}
      onChange={() => undefined} onSubmit={() => undefined} onStop={() => undefined} />)
    const send = host.querySelector<HTMLButtonElement>('button[aria-label="Send"]')!
    expect(send.disabled).toBe(false)
    expect(send.getAttribute("aria-disabled")).toBe("true")
    expect(host.querySelector(".gerr.mut")?.textContent).toBe("Write a question first.")
  })

  it("shows the masked text and the removed note on the sent title", () => {
    mount(<AnswerTitle question="Mera NTN [NTN] hai." redacted context={null} when={null} sourceCount={0}
      sourcesOpen={false} copy={copy} onSources={() => undefined} onAnswer={() => undefined} language={null} />)
    expect(host.querySelector(".q-title mark.mk")?.textContent).toBe("[NTN]")
    expect(host.querySelector(".redsent")?.textContent).toBe("Personal details were removed before this was sent.")
  })
})

describe("tool cards", () => {
  it("renders the filer comparison rows", () => {
    slip(toolTurn("filer_comparison", {
      tax_year: "TY2026", rules_version: "ty2026@1", filer_total: 300000, non_filer_total: 1050000, savings: 750000, notes: [],
      rows: [{ type: "property_purchase", amount: 10000000, filer_tax: 300000, late_filer_tax: null, non_filer_tax: 1050000, difference: 750000, source: { law: "Income Tax Ordinance, 2001", ref: "s.236K" } }],
    }, "On Rs 10,000,000, a filer pays Rs 300,000."))
    const card = host.querySelector('[data-tool-card="filer_comparison"]')!
    expect(card.textContent).toContain("Open Filer check")
    expect(card.querySelectorAll(".fr")).toHaveLength(2)
    expect(card.textContent).toContain("Rs 1,050,000")
    expect(card.textContent).toContain("Rules ty2026@1")
    expect(host.textContent).toContain("a filer pays")
  })

  it("hides the duplicate answer on notice and experts cards", () => {
    slip(toolTurn("notice", { upload: true, message: "Open the Notice page and upload the PDF or photo." }, "Open the Notice page and upload the PDF or photo."))
    expect(host.querySelector('[data-tool-card="notice"]')?.textContent).toContain("Upload the notice")
    expect(host.querySelector("[data-answer-body]")).toBeNull()
    act(() => root.unmount())
    host.remove()
    slip(toolTurn("experts", {
      advice: "These are public listings for that category. Contact them yourself.", advice_ru: "x",
      experts: [
        { id: "a", name: "Example Tax Advisory", city: "Lahore", specialties: ["audit_notice"], profile_url: "https://example.com/", last_updated: "2026-10-14" },
        { id: "b", name: "Second", city: "Lahore", specialties: ["income_tax"], last_updated: "2026-10-12" },
        { id: "c", name: "Third", city: "Lahore", specialties: ["income_tax"] },
      ],
    }, "These are public listings for that category. Contact them yourself."))
    const card = host.querySelector('[data-tool-card="experts"]')!
    expect(card.querySelectorAll(".xr")).toHaveLength(2)
    expect(card.textContent).toContain("Updated 14 Oct 2026")
    expect(host.querySelector("[data-answer-body]")).toBeNull()
  })

  it("renders the checklist and updates cards", () => {
    slip(toolTurn("checklist", {
      id: "c1", title: "Register for an NTN", progress: 0,
      steps: [{ id: "s1", title: "Read the registration provision", sources: ["Income Tax Ordinance, 2001, section 181"], done: false }],
    }, "Checklist started: Register for an NTN"))
    expect(host.querySelector('[data-tool-card="checklist"]')?.textContent).toContain("0 of 1 steps")
    expect(host.textContent).toContain("Checklist started: Register for an NTN")
    act(() => root.unmount())
    host.remove()
    slip(toolTurn("updates", {
      page: 1, pages: 9, total: 42,
      items: [1, 2, 3, 4].map((n) => ({ id: `u${n}`, title: `Update ${n}`, doc_type: "SRO", published_at: "2026-10-15", source_url: "https://www.fbr.gov.pk/" })),
    }, "Recent FBR updates: Update 1"))
    const card = host.querySelector('[data-tool-card="updates"]')!
    expect(card.querySelectorAll(".ur")).toHaveLength(3)
    expect(card.textContent).toContain("3 of 42")
  })

  it("falls back to the plain answer for unknown types", () => {
    slip(toolTurn("mystery", { a: 1 }, "Plain answer text."))
    expect(host.querySelector("[data-tool-card]")).toBeNull()
    expect(host.textContent).toContain("Plain answer text.")
  })
})
