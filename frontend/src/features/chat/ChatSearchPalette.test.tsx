/** Search highlights titles and snippets, and Escape closes the palette. */

// @vitest-environment happy-dom
import { createRoot, type Root } from "react-dom/client"
import { act } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { ChatSummary } from "../../api/chat"
import ChatSearchPalette from "./ChatSearchPalette"

const copy = (key: string) =>
  (
    {
      searchChats: "Search chats",
      searchPlaceholder: "Search chats",
      searchEmpty: "No chats match that.",
      searchLabel: "Chats",
      historyToday: "Today",
      historyYesterday: "Yesterday",
      historyPrevious7: "Previous 7 days",
      newChat: "New chat",
      searchMove: "to move",
      searchOpenKey: "to open",
      searchCloseKey: "to close",
    } as Record<string, string>
  )[key] ?? key

function row(id: string, title: string, updated_at: string): ChatSummary {
  return { id, title, created_at: updated_at, updated_at }
}

describe("ChatSearchPalette", () => {
  let root: Root
  let host: HTMLDivElement

  afterEach(() => {
    act(() => root?.unmount())
    host?.remove()
  })

  it("highlights a match and opens it with Enter", async () => {
    const onOpen = vi.fn()
    const onClose = vi.fn()
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(
        <ChatSearchPalette
          chats={[
            row("1", "Freelancer income tax", "2026-10-19T08:00:00Z"),
            row("2", "Crypto notes", "2026-10-19T07:00:00Z"),
          ]}
          snippets={{ "2": "The bank deducts tax at a fixed rate" }}
          copy={copy as never}
          onOpen={onOpen}
          onClose={onClose}
        />,
      )
    })
    const field = document.querySelector("input")
    if (!field) throw new Error("missing search field")
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set
    setter?.call(field, "tax")
    await act(async () => {
      field.dispatchEvent(new Event("input", { bubbles: true }))
    })
    const marks = [...document.querySelectorAll("mark")].map((mark) => mark.textContent)
    expect(marks).toContain("tax")
    expect(document.body.textContent).toContain("Today")
    await act(async () => {
      field.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }))
    })
    await act(async () => {
      field.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }))
    })
    expect(onOpen).toHaveBeenCalledWith("2")
    await act(async () => {
      document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))
    })
    expect(onClose).toHaveBeenCalled()
  })
})
