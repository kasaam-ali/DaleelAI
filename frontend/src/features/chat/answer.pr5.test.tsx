/** PR 5: citation chips, the source panel, law view, Markdown tables, and where the model name shows. */

// @vitest-environment happy-dom
import { act, useState } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { SseEvent, Source } from "../../api/chat"
import { t } from "../../i18n"
import ChatPage from "./ChatPage"
import { copyReference, linkCitations, pdfHref } from "./answer/refs"

const SOURCES: Source[] = [
  {
    library: "verified",
    doc_id: "ito",
    title: "Income Tax Ordinance, 2001",
    section: "149",
    page: 212,
    url: "https://www.fbr.gov.pk/ito.pdf",
    mirror_url: null,
    site: "fbr.gov.pk",
    fetched_at: null,
    snippet: "Every employer shall deduct tax from salary.",
    rerank_score: 0.82,
  },
  {
    library: "verified",
    doc_id: "ito",
    title: "Income Tax Ordinance, 2001",
    section: "114",
    page: 198,
    url: "https://www.fbr.gov.pk/ito.pdf",
    mirror_url: null,
    site: "fbr.gov.pk",
    fetched_at: null,
    snippet: "Every person shall furnish a return of income.",
    rerank_score: 0.7,
  },
]

const ANSWER = [
  "### Short answer",
  "Your employer deducts tax every month [1]. You still file a return [2]. Marker [7] has no source.",
  "",
  "| Case | Rate | Ref |",
  "| --- | --- | --- |",
  "| Salaried | Slab | s.149 |",
  "",
  "<script>alert(1)</script>",
].join("\n")

vi.mock("../../api/chat", () => ({
  streamChat: vi.fn(async (_body: unknown, _session: string, onEvent: (event: SseEvent) => void) => {
    onEvent({
      event: "meta",
      data: { chat_id: "chat-1", message_id: "message-1", intent: "qa", language: "en", tax_year: "TY2026" },
    })
    onEvent({ event: "sources", data: { sources: SOURCES } })
    onEvent({
      event: "final",
      data: {
        answer: ANSWER,
        answer_source: "verified",
        confidence: "high",
        verified: true,
        model: "groq/llama-3.3-70b",
        tax_year: "TY2026",
        corpus_date: "2026-07-01",
        action_links: [],
        follow_ups: ["When is the return deadline?"],
        cached: false,
        trace: { intent: "qa", search_query: "salary tax", retrieved: 24, rerank_top: 0.82, verified: true, latency_ms: 4100 },
      },
    })
    onEvent({ event: "done", data: {} })
  }),
  getChat: vi.fn(() => new Promise(() => undefined)),
  sendFeedback: vi.fn(async () => undefined),
}))

function Harness() {
  const [chatId, setChatId] = useState<string | null>(null)
  return (
    <ChatPage
      language="en"
      profile={{ taxpayer_type: null, filer_status: null, province: null }}
      copy={(key) => t("en", key)}
      chatId={chatId}
      sessionId="session-1"
      onChatId={setChatId}
      onActivity={() => undefined}
    />
  )
}

describe("PR 5 answer view", () => {
  let root: Root
  let host: HTMLDivElement

  afterEach(() => {
    act(() => root?.unmount())
    host?.remove()
    localStorage.clear()
  })

  async function render() {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    const field = document.querySelector("textarea")
    if (!field) throw new Error("missing composer")
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set
    setter?.call(field, "Salary tax?")
    field.dispatchEvent(new Event("input", { bubbles: true }))
    await act(async () => {
      field.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }))
    })
    await act(async () => {
      await Promise.resolve()
    })
  }

  const chips = () => [...host.querySelectorAll<HTMLButtonElement>("[data-answer-body] button.cite")]

  it("turns only real [n] markers into named chips, and renders sanitized Markdown tables", async () => {
    await render()
    expect(chips().map((chip) => chip.textContent)).toEqual(["1", "2"])
    expect(chips()[0].getAttribute("aria-label")).toBe("Source 1: ITO 2001 · s.149")
    expect(host.querySelector("[data-answer-body]")?.textContent).toContain("[7]")
    expect(host.querySelector(".tw table td.ref")?.textContent).toBe("s.149")
    expect(host.querySelector("[data-answer-body] script")).toBeNull()
    expect(host.querySelector("[data-answer-body] h3")?.textContent).toBe("Short answer")
  })

  it("opens the panel from a chip, focuses its heading, and Esc returns focus to the chip", async () => {
    await render()
    const chip = chips()[1]
    expect(chip.getAttribute("aria-pressed")).toBe("false")
    expect(chip.getAttribute("aria-controls")).toBe(host.querySelector("[data-source-panel]")?.id ?? chip.getAttribute("aria-controls"))
    await act(async () => {
      chip.click()
    })
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0))
    })
    const panel = host.querySelector<HTMLElement>("[data-source-panel]")
    expect(panel).not.toBeNull()
    expect(panel?.id).toBe(chip.getAttribute("aria-controls"))
    expect(document.activeElement?.tagName).toBe("H2")
    expect(panel?.textContent).toContain("ITO 2001 · s.114")
    expect(panel?.querySelector<HTMLAnchorElement>("a.primary")?.getAttribute("href")).toBe("https://www.fbr.gov.pk/ito.pdf#page=198")
    expect(chips()[1].getAttribute("aria-pressed")).toBe("true")
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))
    })
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0))
    })
    expect(host.querySelector("[data-source-panel]")).toBeNull()
    expect(document.activeElement).toBe(chips()[1])
  })

  it("opens the law view with the highlighted snippet; Esc goes back to the panel", async () => {
    await render()
    await act(async () => {
      chips()[0].click()
    })
    const lawButton = [...host.querySelectorAll("button")].find((button) => button.textContent?.includes("Open in law view"))
    await act(async () => {
      lawButton?.click()
    })
    const law = host.querySelector("[data-law-view]")
    expect(law?.querySelector("mark")?.textContent).toBe(SOURCES[0].snippet)
    expect(law?.textContent).toContain("Highlighted: the passage this answer relies on")
    expect(host.querySelector(".a-grid.law-split")).not.toBeNull()
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))
    })
    expect(host.querySelector("[data-law-view]")).toBeNull()
    expect(host.querySelector("[data-source-panel]")).not.toBeNull()
  })

  it("shows the model name only inside How this was answered", async () => {
    await render()
    const how = host.querySelector("[data-how-answered]")
    expect(how?.textContent).toContain("groq/llama-3.3-70b")
    const outside = host.textContent?.replace(how?.textContent ?? "", "") ?? ""
    expect(outside).not.toContain("groq/llama-3.3-70b")
    expect(host.querySelector("[data-trust]")?.getAttribute("data-trust")).toBe("verified")
  })

  it("builds the copy reference and the page link", () => {
    expect(copyReference(SOURCES[0], "TY2026")).toBe("Income Tax Ordinance, 2001, s.149, p.212 (TY2026)")
    expect(pdfHref(SOURCES[0])).toBe("https://www.fbr.gov.pk/ito.pdf#page=212")
    expect(pdfHref({ ...SOURCES[0], url: "javascript:alert(1)" })).toBeNull()
    expect(linkCitations("a [1] b [3] c [1](x)", 2)).toBe("a [1](#cite-1) b [3] c [1](x)")
  })
})
