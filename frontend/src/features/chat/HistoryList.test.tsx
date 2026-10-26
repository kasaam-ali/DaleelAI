/** Menu, rename, delete confirm, and focus after delete. */

// @vitest-environment happy-dom
Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
import { createRoot, type Root } from "react-dom/client"
import { act, type ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { ChatSummary } from "../../api/chat"
import HistoryList from "./HistoryList"

const copy = (key: string) =>
  (
    {
      historyToday: "Today",
      historyYesterday: "Yesterday",
      historyPrevious7: "Previous 7 days",
      newChat: "New chat",
      recentChats: "Recent",
      noChats: "No chats on this device yet.",
      chatActions: "Chat actions",
      renameChat: "Rename",
      copyChatLink: "Copy link",
      deleteChat: "Delete",
      renameSave: "Save name",
      renameCancel: "Cancel rename",
      deleteChatTitle: "Delete this chat?",
      deleteChatBody: "and its answers will be deleted from the server. This can't be undone.",
      deleteChatConfirm: "Delete chat",
      deleteChatCancel: "Cancel",
      linkCopied: "Link copied.",
      linkCopyFailed: "The link could not be copied.",
      renameFailed: "The chat could not be renamed.",
      deleteFailed: "The chat could not be deleted.",
      titleInvalid: "Title must be 1 to 80 characters.",
    } as Record<string, string>
  )[key] ?? key

function row(id: string, title: string): ChatSummary {
  return {
    id,
    title,
    created_at: "2026-10-19T08:00:00Z",
    updated_at: "2026-10-19T08:00:00Z",
  }
}

describe("HistoryList", () => {
  let root: Root
  let host: HTMLDivElement

  afterEach(() => {
    act(() => root?.unmount())
    host?.remove()
    document.body.innerHTML = ""
  })

  async function render(ui: ReactNode) {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(ui)
    })
  }

  it("renames from the menu and rejects an empty title", async () => {
    const onRename = vi.fn(async () => undefined)
    await render(
      <HistoryList
        chats={[row("chat-1", "Freelancer income tax")]}
        activeId="chat-1"
        copy={copy as never}
        onSelect={() => undefined}
        onRename={onRename}
        onDelete={async () => undefined}
        onOpenNew={() => undefined}
        onToast={() => undefined}
      />,
    )
    const menuButton = document.querySelector<HTMLButtonElement>("[data-history-menu]")
    await act(async () => {
      menuButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    })
    expect(document.body.textContent).toContain("Rename")
    expect(document.body.textContent).toContain("Copy link")
    expect(document.body.textContent).toContain("Delete")

    await act(async () => {
      document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))
    })
    expect(document.querySelector("[role=menu]")).toBeNull()

    await act(async () => {
      menuButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    })
    const rename = [...document.querySelectorAll("button")].find((button) => button.textContent === "Rename")
    await act(async () => {
      rename?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    })
    const field = document.querySelector("input")
    if (!field) throw new Error("missing rename field")
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set
    setter?.call(field, "   ")
    field.dispatchEvent(new Event("input", { bubbles: true }))
    await act(async () => {
      field.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }))
      field.form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }))
    })
    expect(onRename).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain("Title must be 1 to 80 characters.")

    setter?.call(field, "Salary tax")
    field.dispatchEvent(new Event("input", { bubbles: true }))
    await act(async () => {
      field.form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }))
    })
    expect(onRename).toHaveBeenCalledWith("chat-1", "Salary tax")
  })

  it("focuses cancel, traps the dialog, and moves focus to the next chat", async () => {
    const onDelete = vi.fn(async () => undefined)
    const onOpenNew = vi.fn()
    const button = document.createElement("button")
    button.dataset.newChat = ""
    document.body.append(button)
    await render(
      <HistoryList
        chats={[row("chat-1", "Freelancer income tax"), row("chat-2", "Crypto")]}
        activeId="chat-1"
        copy={copy as never}
        onSelect={() => undefined}
        onRename={async () => undefined}
        onDelete={onDelete}
        onOpenNew={onOpenNew}
        onToast={() => undefined}
      />,
    )
    await act(async () => {
      document.querySelector<HTMLButtonElement>("[data-history-menu]")?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    })
    const remove = [...document.querySelectorAll("button")].find((item) => item.textContent === "Delete")
    await act(async () => {
      remove?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    })
    const dialog = document.querySelector("[role=alertdialog]")
    expect(dialog?.textContent).toContain("Delete this chat?")
    expect(dialog?.textContent).toContain("Freelancer income tax")
    const cancel = [...document.querySelectorAll("button")].find((item) => item.textContent === "Cancel")
    const confirm = [...document.querySelectorAll("button")].find((item) => item.textContent === "Delete chat")
    expect(document.activeElement).toBe(cancel)
    confirm?.focus()
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }))
    })
    expect(document.activeElement).toBe(cancel)
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true, shiftKey: true }))
    })
    expect(document.activeElement).toBe(confirm)

    await act(async () => {
      confirm?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    })
    expect(onDelete).toHaveBeenCalledWith("chat-1")
    expect(onOpenNew).toHaveBeenCalled()
    await act(async () => {
      await new Promise((resolve) => requestAnimationFrame(() => resolve(undefined)))
    })
    expect(document.activeElement).toBe(document.querySelector("[data-history-id='chat-2']"))
  })
})
