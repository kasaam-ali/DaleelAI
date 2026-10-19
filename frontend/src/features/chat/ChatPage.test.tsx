/** Checks that a streamed answer shows up on the chat page. */

// @vitest-environment happy-dom
import { StrictMode, useState } from "react"
import { createRoot, type Root } from "react-dom/client"
import { act } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { getChat, streamChat, type SseEvent } from "../../api/chat"
import ChatPage from "./ChatPage"

const events: { onEvent: ((event: SseEvent) => void) | null; release: (() => void) | null } = {
  onEvent: null,
  release: null,
}
const history: {
  release: ((messages: unknown[]) => void) | null
  fail: (() => void) | null
} = { release: null, fail: null }

vi.mock("../../api/chat", () => ({
  streamChat: vi.fn(async (body: { message?: string }, _session: string, onEvent: (event: SseEvent) => void) => {
    events.onEvent = onEvent
    const message = body.message ?? ""
    onEvent({
      event: "meta",
      data: {
        chat_id: "chat-1",
        message_id: "message-1",
        intent: "qa",
        language: /\b(hai|kya|kitna|kaise)\b/i.test(message) ? "roman_urdu" : "en",
        tax_year: "TY2027",
      },
    })
    await new Promise<void>((resolve) => {
      events.release = resolve
    })
    onEvent({ event: "token", data: { text: "Section 149" } })
    onEvent({
      event: "final",
      data: {
        answer: "Section 149 covers the rule.",
        answer_source: "verified",
        confidence: "medium",
        verified: false,
        model: "test",
        tax_year: "TY2027",
        corpus_date: "2026-01-01",
        action_links: [],
        follow_ups: [],
        cached: false,
      },
    })
    onEvent({ event: "done", data: {} })
  }),
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
    localStorage.clear()
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
})
