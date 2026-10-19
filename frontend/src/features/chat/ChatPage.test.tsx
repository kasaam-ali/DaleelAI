/** Checks that a streamed answer shows up on the chat page. */

// @vitest-environment happy-dom
import { StrictMode, useState } from "react"
import { createRoot, type Root } from "react-dom/client"
import { act } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { getChat, streamChat, type SseEvent, type Source } from "../../api/chat"
import ChatPage from "./ChatPage"

const script = vi.hoisted(() => ({
  intent: "qa",
  answerSource: "verified" as "verified" | "web" | "none",
  sources: [] as Source[],
  model: "test",
  hang: false,
  fail: null as null | { status: number; code: string; message: string },
}))

const events: { onEvent: ((event: SseEvent) => void) | null; release: (() => void) | null } = {
  onEvent: null,
  release: null,
}
const history: {
  release: ((messages: unknown[]) => void) | null
  fail: (() => void) | null
} = { release: null, fail: null }

vi.mock("../../api/chat", () => ({
  streamChat: vi.fn(
    async (body: { message?: string }, _session: string, onEvent: (event: SseEvent) => void, signal?: AbortSignal) => {
    if (script.fail) {
      const failure = Object.assign(new Error(script.fail.message), {
        status: script.fail.status,
        code: script.fail.code,
      })
      throw failure
    }
    events.onEvent = onEvent
    const message = body.message ?? ""
    onEvent({
      event: "meta",
      data: {
        chat_id: "chat-1",
        message_id: "message-1",
        intent: script.intent,
        language: /\b(hai|kya|kitna|kaise)\b/i.test(message) ? "roman_urdu" : "en",
        tax_year: "TY2027",
      },
    })
    if (script.hang) {
      await new Promise<void>((_resolve, reject) => {
        if (signal?.aborted) {
          reject(Object.assign(new Error("aborted"), { name: "AbortError" }))
          return
        }
        signal?.addEventListener("abort", () => {
          reject(Object.assign(new Error("aborted"), { name: "AbortError" }))
        })
      })
      return
    }
    if (script.sources.length > 0) onEvent({ event: "sources", data: { sources: script.sources } })
    await new Promise<void>((resolve) => {
      events.release = resolve
    })
    onEvent({ event: "token", data: { text: "Section 149" } })
    onEvent({
      event: "final",
      data: {
        answer: "Section 149 covers the rule.",
        answer_source: script.answerSource,
        confidence: "medium",
        verified: false,
        model: script.model,
        tax_year: "TY2027",
        corpus_date: "2026-01-01",
        action_links: [],
        follow_ups: [],
        cached: false,
        trace: {
          intent: script.intent,
          search_query: "section 149",
          retrieved: 0,
          rerank_top: null,
          verified: false,
          latency_ms: 10,
        },
      },
    })
    onEvent({ event: "done", data: {} })
  },
  ),
  getChat: vi.fn(
    () =>
      new Promise((resolve, reject) => {
        history.release = (messages) =>
          resolve({
            id: "old-chat",
            title: "",
            created_at: "",
            updated_at: "",
            messages,
          })
        history.fail = () => reject(new Error("not_found"))
      }),
  ),
  sendFeedback: vi.fn(async () => undefined),
}))

function Harness({ initialChatId = null }: { initialChatId?: string | null }) {
  const [chatId, setChatId] = useState<string | null>(initialChatId)
  return (
    <StrictMode>
      <button type="button" onClick={() => setChatId(null)}>
        new-chat
      </button>
      <ChatPage
        language="en"
        profile={{ taxpayer_type: null, filer_status: null, province: null }}
        copy={(key) => key}
        chatId={chatId}
        sessionId="session-1"
        onChatId={setChatId}
        onActivity={() => undefined}
      />
    </StrictMode>
  )
}

describe("ChatPage live answer", () => {
  let root: Root
  let host: HTMLDivElement

  afterEach(() => {
    act(() => root?.unmount())
    host?.remove()
    events.onEvent = null
    events.release = null
    history.release = null
    history.fail = null
    script.intent = "qa"
    script.answerSource = "verified"
    script.sources = []
    script.model = "test"
    script.hang = false
    script.fail = null
    Object.defineProperty(navigator, "onLine", { configurable: true, value: true })
    window.dispatchEvent(new Event("online"))
    localStorage.clear()
    vi.useRealTimers()
  })

  async function send(question: string) {
    const field = document.querySelector("textarea")
    if (!field) throw new Error("missing composer")
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set
    setter?.call(field, question)
    field.dispatchEvent(new Event("input", { bubbles: true }))
    await act(async () => {
      field.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }))
    })
  }

  it("keeps the question and the late token on screen", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await send("What does section 149 cover?")
    expect(host.textContent).toContain("What does section 149 cover?")
    expect(host.textContent).not.toContain("emptyGreeting")

    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })

    expect(host.textContent).toContain("What does section 149 cover?")
    expect(host.textContent).toContain("Section 149")
    expect(host.textContent).not.toContain("emptyGreeting")
    expect(vi.mocked(getChat)).not.toHaveBeenCalled()
  })

  it("keeps the new answer when an older history load finishes late", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness initialChatId="old-chat" />)
    })
    await act(async () => {
      host.querySelector("button")?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    })
    await send("What does section 149 cover?")
    expect(host.textContent).toContain("What does section 149 cover?")

    await act(async () => {
      history.release?.([])
      await Promise.resolve()
    })
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })

    expect(host.textContent).toContain("What does section 149 cover?")
    expect(host.textContent).toContain("Section 149")
    expect(host.textContent).not.toContain("emptyGreeting")
  })

  it("keeps the late token when the new chat history fails", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness initialChatId="chat-1" />)
    })
    await send("What does section 149 cover?")
    expect(host.textContent).toContain("What does section 149 cover?")

    await act(async () => {
      history.fail?.()
      await Promise.resolve()
    })
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })

    expect(host.textContent).toContain("What does section 149 cover?")
    expect(host.textContent).toContain("Section 149")
    expect(host.textContent).not.toContain("emptyGreeting")
  })

  it("asks in auto, then resends in English when EN is chosen", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    vi.mocked(streamChat).mockClear()
    await send("Freelance income pe kitna tax hai?")
    const first = vi.mocked(streamChat).mock.calls[0]?.[0] as { language: string; message: string }
    expect(first.language).toBe("auto")
    expect(first.message).toBe("Freelance income pe kitna tax hai?")

    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
    expect(host.textContent).toContain("detectedRomanUrdu")
    expect(host.textContent).toContain("Roman Urdu")
    expect(host.textContent).not.toContain("اردو")
    const checked = host.querySelector('[role="radio"][aria-checked="true"]')
    expect(checked?.textContent).toBe("Roman Urdu")
    expect(localStorage.getItem("daleelai.answer_language") ?? "").not.toContain("roman_urdu")

    const english = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "EN")
    await act(async () => {
      english?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
      await Promise.resolve()
    })
    const again = vi.mocked(streamChat).mock.calls.at(-1)?.[0] as { language: string; message: string }
    expect(again.language).toBe("en")
    expect(again.message).toBe("Freelance income pe kitna tax hai?")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
  })

  it("detects the next question until the user picks a language", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await send("What does section 149 cover?")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
    vi.mocked(streamChat).mockClear()
    await send("NTN registration kaise karte hain?")
    const second = vi.mocked(streamChat).mock.calls[0]?.[0] as { language: string; message: string }
    expect(second.language).toBe("auto")
    expect(second.message).toBe("NTN registration kaise karte hain?")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
  })

  it("shows the source strip before the answer text", async () => {
    script.sources = [
      {
        library: "verified",
        doc_id: "ito",
        title: "Income Tax Ordinance",
        section: "149",
        page: 12,
        url: "https://www.fbr.gov.pk/",
        mirror_url: null,
        site: "fbr.gov.pk",
        fetched_at: null,
        snippet: "Salary",
        rerank_score: null,
      },
    ]
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await send("What does section 149 cover?")
    expect(host.textContent).toContain("checkingSources")
    expect(host.textContent).toContain("Income Tax Ordinance")
    expect(host.textContent).not.toContain("Section 149 covers the rule.")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
  })

  it("shows the provider chip and resends the same question", async () => {
    script.fail = {
      status: 503,
      code: "providers_busy",
      message: "All AI providers are busy right now.",
    }
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    vi.mocked(streamChat).mockClear()
    await send("What does section 149 cover?")
    expect(host.textContent).toContain("503 · Providers busy")
    expect(host.textContent).toContain("All AI providers are busy right now.")
    expect(host.textContent).toContain("autoRetrySaved")
    expect(host.textContent).toContain("20")
    expect(host.querySelector('[role="status"] button')?.textContent).toBe("cancelAutoRetry")
    const retry = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "retry")
    await act(async () => {
      retry?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
      await Promise.resolve()
    })
    const again = vi.mocked(streamChat).mock.calls.at(-1)?.[0] as { message: string }
    expect(vi.mocked(streamChat).mock.calls.length).toBeGreaterThan(1)
    expect(again.message).toBe("What does section 149 cover?")
  })

  it("counts down a 429 and leaves the question in place when cancelled", async () => {
    vi.useFakeTimers()
    script.fail = {
      status: 429,
      code: "rate_limited",
      message: "Too many requests right now.",
    }
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    vi.mocked(streamChat).mockClear()
    await send("What does section 149 cover?")
    expect(host.textContent).toContain("429 · Too many requests")
    expect(host.textContent).toContain("Too many requests right now.")
    expect(host.textContent).toContain("20")
    const retry = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "retry")
    const cancel = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "cancelAutoRetry")
    expect(retry).toBeTruthy()
    expect(cancel).toBeTruthy()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(host.textContent).toContain("19")
    await act(async () => {
      cancel?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    })
    const calls = vi.mocked(streamChat).mock.calls.length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(vi.mocked(streamChat).mock.calls.length).toBe(calls)
    expect(host.textContent).toContain("What does section 149 cover?")
    vi.useRealTimers()
  })

  it("renders a refusal card for each limit, not a failed verification", async () => {
    const cases = [
      { intent: "qa", answerSource: "none" as const, title: "refusalEvidenceTitle" },
      { intent: "out_of_scope", answerSource: "verified" as const, title: "refusalScopeTitle" },
      { intent: "refuse", answerSource: "none" as const, title: "refusalDeclinedTitle" },
      { intent: "provincial", answerSource: "none" as const, title: "refusalProvincialTitle" },
    ]
    for (const item of cases) {
      act(() => root?.unmount())
      host?.remove()
      script.intent = item.intent
      script.answerSource = item.answerSource
      host = document.createElement("div")
      document.body.append(host)
      root = createRoot(host)
      await act(async () => {
        root.render(<Harness />)
      })
      await send("What does section 149 cover?")
      await act(async () => {
        events.release?.()
        await Promise.resolve()
      })
      expect(host.textContent).toContain(item.title)
      expect(host.textContent).not.toContain("notVerified")
    }
  })

  it("queues a question while offline and sends it once the browser is back", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await act(async () => {
      window.dispatchEvent(new Event("offline"))
    })
    vi.mocked(streamChat).mockClear()
    await send("What does section 149 cover?")
    expect(host.textContent).toContain("queued")
    expect(host.textContent).toContain("offlineBanner")
    expect(vi.mocked(streamChat)).not.toHaveBeenCalled()
    await act(async () => {
      window.dispatchEvent(new Event("online"))
      await Promise.resolve()
    })
    expect(vi.mocked(streamChat)).toHaveBeenCalled()
    const sent = vi.mocked(streamChat).mock.calls.at(-1)?.[0] as { message: string }
    expect(sent.message).toBe("What does section 149 cover?")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
  })

  it("keeps a saved demo answer instead of an evidence refusal", async () => {
    script.intent = "qa"
    script.answerSource = "none"
    script.model = "demo-cache"
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await send("Demo: section 149 kya cover karta hai?")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
    expect(host.textContent).toContain("Section 149 covers the rule.")
    expect(host.textContent).not.toContain("refusalEvidenceTitle")
  })

  it("shows a stopped answer with retry instead of a frozen skeleton", async () => {
    script.hang = true
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await send("What does section 149 cover?")
    expect(host.textContent).toContain("checkingLibrary")
    const stop = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "stop")
    await act(async () => {
      stop?.click()
      await Promise.resolve()
    })
    expect(host.textContent).toContain("stoppedTitle")
    expect(host.textContent).toContain("retry")
    expect(host.textContent).not.toContain("checkingLibrary")
    script.hang = false
    const retry = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "retry")
    await act(async () => {
      retry?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
      await Promise.resolve()
    })
    expect(vi.mocked(streamChat).mock.calls.length).toBeGreaterThan(1)
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
    expect(host.textContent).toContain("Section 149 covers the rule.")
  })

  it("keeps the citation step visible after the first token", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await send("What does section 149 cover?")
    await act(async () => {
      events.onEvent?.({ event: "token", data: { text: "Section 149" } })
      events.onEvent?.({ event: "step", data: { node: "verify", status: "start" } })
      await Promise.resolve()
    })
    expect(host.textContent).toContain("Section 149")
    expect(host.textContent).toContain("stepCheck")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
  })

  it("re-asks an earlier message in the language that was chosen", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await send("What does section 149 cover?")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
    await send("How is salary taxed?")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
    const groups = host.querySelectorAll('[role="radiogroup"]')
    expect(groups.length).toBe(2)
    const roman = Array.from(groups[0].querySelectorAll("button")).find((button) => button.textContent === "Roman Urdu")
    vi.mocked(streamChat).mockClear()
    await act(async () => {
      roman?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
      await Promise.resolve()
    })
    const again = vi.mocked(streamChat).mock.calls[0]?.[0] as { language: string; message: string }
    expect(again.language).toBe("roman_urdu")
    expect(again.message).toBe("What does section 149 cover?")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
  })

  it("restores a queued question after a reload while offline", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await act(async () => {
      window.dispatchEvent(new Event("offline"))
    })
    vi.mocked(streamChat).mockClear()
    await send("What does section 149 cover?")
    expect(localStorage.getItem("daleelai.offline_queue") ?? "").toContain("What does section 149 cover?")
    await act(async () => {
      root.unmount()
    })
    host.remove()
    Object.defineProperty(navigator, "onLine", { configurable: true, value: false })
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    expect(host.textContent).toContain("queued")
    expect(host.textContent).toContain("What does section 149 cover?")
    expect(vi.mocked(streamChat)).not.toHaveBeenCalled()
    await act(async () => {
      Object.defineProperty(navigator, "onLine", { configurable: true, value: true })
      window.dispatchEvent(new Event("online"))
      await Promise.resolve()
    })
    expect(vi.mocked(streamChat)).toHaveBeenCalled()
    const sent = vi.mocked(streamChat).mock.calls.at(-1)?.[0] as { message: string }
    expect(sent.message).toBe("What does section 149 cover?")
    await act(async () => {
      events.release?.()
      await Promise.resolve()
    })
    expect(localStorage.getItem("daleelai.offline_queue")).toBeNull()
  })

  it("keeps a queued question when the send is cut off", async () => {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(<Harness />)
    })
    await act(async () => {
      window.dispatchEvent(new Event("offline"))
    })
    await send("What does section 149 cover?")
    script.fail = { status: 500, code: "server_error", message: "Server error." }
    await act(async () => {
      window.dispatchEvent(new Event("online"))
      await Promise.resolve()
    })
    expect(localStorage.getItem("daleelai.offline_queue") ?? "").toContain("What does section 149 cover?")
    expect(host.textContent).toContain("queueHeld")
    expect(host.textContent).toContain("queued")
  })
})
