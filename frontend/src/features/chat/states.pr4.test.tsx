/** PR 4 (SPEC §5.2A items 3, 9–11; §5.3; §6): steps card, error card, offline banner and the four refusal kinds. */

// @vitest-environment happy-dom
import { act } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { t, type CopyKey } from "../../i18n"
import ErrorCard from "./ErrorCard"
import { shortRequestId } from "./failure"
import OfflineBanner from "./OfflineBanner"
import RefusalCard from "./RefusalCard"
import StatusSteps from "./StatusSteps"

const en = (key: CopyKey) => t("en", key)
const ru = (key: CopyKey) => t("roman_urdu", key)
let root: Root
let host: HTMLDivElement
beforeEach(() => {
  host = document.createElement("div")
  document.body.append(host)
  root = createRoot(host)
})
afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

describe("StatusSteps", () => {
  it("done = check + time, active = ring + detail, to-do = muted with no detail; the header follows the stage", () => {
    act(() => root.render(<StatusSteps phases={["done", "active", "pending", "pending"]} times={[0.4, null, null, null]} copy={en} />))
    const rows = Array.from(host.querySelectorAll(".psteps li"))
    expect(rows.map((row) => row.className)).toEqual(["done", "act", "todo", "todo"])
    expect(rows[0].querySelector(".s svg")).not.toBeNull()
    expect(rows[0].querySelector(".t")?.textContent).toBe("0.4s")
    expect(rows[1].querySelector("small")?.textContent).toBe(en("stepLibrarySub"))
    expect(rows[2].querySelector("small")).toBeNull()
    expect(host.querySelector(".working")?.textContent).toBe("Checking the FBR library…")
    expect(host.querySelectorAll(".sk-strip .sk")).toHaveLength(4)
    act(() => root.render(<StatusSteps phases={["done", "done", "active", "pending"]} copy={ru} skeleton={false} />))
    expect(host.querySelector(".working")?.textContent).toBe("Jawab likh raha hoon…")
    expect(Array.from(host.querySelectorAll(".psteps b")).map((b) => b.textContent)).toEqual([
      "Sawal samjha",
      "Library dhoond raha hoon…",
      "Jawab likh raha hoon",
      "Hawalay check kar raha hoon",
    ])
    expect(host.querySelector(".sk-strip")).toBeNull()
  })
})

describe("ErrorCard", () => {
  const busy = { status: 503, code: "providers_busy", message: "providers_busy: groq 503, gemini 503" }
  it("503: chip, plain reason, real message, Retry now, Copy question, countdown timer + Cancel, saved + request id", () => {
    const onCancel = vi.fn()
    act(() =>
      root.render(
        <ErrorCard error={busy} secondsLeft={14} totalSeconds={14} requestId="7f3ac21e-0000-4000-8000-000000000000" copy={en} onRetry={vi.fn()} onCopy={vi.fn()} onCancel={onCancel} />,
      ),
    )
    expect(host.querySelector("[data-error-code]")?.textContent).toBe("503 · Providers busy")
    expect(host.textContent).toContain("The answer didn't arrive")
    expect(host.textContent).toContain(en("errPlain503"))
    expect(host.querySelector(".realmsg")?.textContent).toBe(busy.message)
    const timer = host.querySelector('[role="timer"]')!
    expect(timer.getAttribute("aria-live")).toBe("off")
    expect(timer.textContent).toBe("Auto-retry in 14 s")
    expect(host.textContent).toContain("Retry now")
    expect(host.textContent).toContain("Copy question")
    expect(host.textContent).toContain("Your question is saved. Request id 7f3a·c21e")
    act(() => host.querySelector<HTMLButtonElement>("[data-cancel-auto-retry]")!.click())
    expect(onCancel).toHaveBeenCalledOnce()
  })
  it("after Cancel: the ring is replaced by the cancelled line and Retry now stays (Roman Urdu)", () => {
    act(() => root.render(<ErrorCard error={busy} secondsLeft={null} cancelled copy={ru} onRetry={vi.fn()} onCopy={vi.fn()} onCancel={vi.fn()} />))
    expect(host.querySelector('[role="timer"]')).toBeNull()
    expect(host.querySelector("[data-auto-retry-off]")?.textContent).toBe("Auto-retry band. Jab chahein dobara koshish karein.")
    expect(host.textContent).toContain("Abhi dobara koshish")
    expect(host.textContent).toContain("Jawab nahi aa saka")
  })
  it("non-503 errors show no invented plain reason", () => {
    act(() => root.render(<ErrorCard error={{ status: 500, code: "internal", message: "Server error." }} secondsLeft={null} copy={en} onRetry={vi.fn()} onCopy={vi.fn()} onCancel={vi.fn()} />))
    expect(host.textContent).not.toContain(en("errPlain503"))
    expect(host.querySelector(".realmsg")?.textContent).toBe("Server error.")
  })
  it("formats the short request id", () => {
    expect(shortRequestId("7f3ac21e-1111-4000-8000-000000000000")).toBe("7f3a·c21e")
  })
})

describe("OfflineBanner", () => {
  it("bold title + body, as a status", () => {
    act(() => root.render(<OfflineBanner queuedCount={0} copy={en} />))
    const banner = host.querySelector('[role="status"].offline-bar')!
    expect(banner.querySelector("b")?.textContent).toBe("You're offline")
    expect(banner.textContent).toContain("Your question will send automatically when you're back online.")
  })
})

describe("RefusalCard kinds", () => {
  const base = { reason: "r", authority: null, query: null, retrieved: null, suggestions: [], links: [], onAsk: vi.fn() }
  it("evidence: violet accent, open 'What I searched' with the trace rows only", () => {
    act(() => root.render(<RefusalCard {...base} kind="evidence" query="crypto income tax" retrieved={24} rerankTop={0.31} copy={en} />))
    const card = host.querySelector<HTMLElement>(".rcard")!
    expect(card.dataset.kind).toBe("evidence")
    expect(card.style.getPropertyValue("--k")).toBe("var(--refusal)")
    expect(host.querySelector("details.searched")?.hasAttribute("open")).toBe(true)
    expect(host.querySelector(".sq")?.textContent).toBe("crypto income tax")
    expect(Array.from(host.querySelectorAll(".miss")).map((row) => row.querySelector("span")?.textContent)).toEqual([
      "24",
      "0.31",
      "0 · no answer was written",
    ])
    expect(Array.from(host.querySelectorAll(".rlink b")).map((b) => b.textContent)).toEqual(["FBR helpline", "FBR tax laws"])
    expect(host.textContent).not.toContain("Not verified")
  })
  for (const [kind, accent, line] of [
    ["scope", "var(--link)", "Not searched: the question isn't about tax"],
    ["declined", "var(--error)", "Not searched: the request was declined"],
    ["provincial", "var(--warn)", "Federal library not used: provincial authority"],
  ] as const) {
    it(`${kind}: ${accent} accent and the not-searched line`, () => {
      act(() => root.render(<RefusalCard {...base} kind={kind} copy={en} />))
      const card = host.querySelector<HTMLElement>(".rcard")!
      expect(card.style.getPropertyValue("--k")).toBe(accent)
      expect(host.querySelector(".notsearched")?.textContent).toBe(line)
      expect(host.querySelector("details.searched")).toBeNull()
    })
  }
  it("declined lists IRIS then the helpline under 'File the right way'", () => {
    act(() => root.render(<RefusalCard {...base} kind="declined" copy={en} />))
    expect(Array.from(host.querySelectorAll(".rsec h4")).map((h) => h.textContent)).toContain("File the right way")
    expect(Array.from(host.querySelectorAll(".rlink b")).map((b) => b.textContent)).toEqual(["File on IRIS", "FBR helpline"])
  })
})
