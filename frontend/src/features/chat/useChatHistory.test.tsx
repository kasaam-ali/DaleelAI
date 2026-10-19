/** Rename rolls back. Delete drops the row after the server accepts it. */

// @vitest-environment happy-dom
Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"
import { createRoot, type Root } from "react-dom/client"
import { act } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { deleteChat, renameChat } from "../../api/chat"
import { useChatHistory } from "./useChatHistory"

const rows = vi.hoisted(() => [
  { id: "c1", title: "Old title", created_at: "2026-10-19T00:00:00Z", updated_at: "2026-10-19T00:00:00Z" },
])

vi.mock("../../api/chat", () => ({
  listChats: vi.fn(async () => rows.map((row) => ({ ...row }))),
  renameChat: vi.fn(),
  deleteChat: vi.fn(async (_sessionId: string, chatId: string) => {
    const index = rows.findIndex((row) => row.id === chatId)
    if (index >= 0) rows.splice(index, 1)
  }),
  getChat: vi.fn(),
}))

function Probe() {
  const history = useChatHistory("session-1")
  const [note, setNote] = useState("")
  return (
    <div>
      <p>{history.chats.map((chat) => chat.title).join("|")}</p>
      <p>{note}</p>
      <button
        type="button"
        onClick={() => {
          void history.rename("c1", "New title").catch((error: Error) => setNote(error.message))
        }}
      >
        rename
      </button>
      <button
        type="button"
        onClick={() => {
          void history.remove("c1")
        }}
      >
        remove
      </button>
    </div>
  )
}

describe("useChatHistory", () => {
  let root: Root
  let host: HTMLDivElement

  afterEach(() => {
    act(() => root?.unmount())
    host?.remove()
    rows.splice(0, rows.length, {
      id: "c1",
      title: "Old title",
      created_at: "2026-10-19T00:00:00Z",
      updated_at: "2026-10-19T00:00:00Z",
    })
    vi.clearAllMocks()
  })

  async function render() {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    await act(async () => {
      root.render(
        <QueryClientProvider client={client}>
          <Probe />
        </QueryClientProvider>,
      )
    })
    for (let attempt = 0; attempt < 20 && !host.textContent?.includes("Old title"); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0))
      })
    }
  }

  it("rolls a failed rename back to the previous title", async () => {
    let rejectRename: (error: Error) => void = () => undefined
    vi.mocked(renameChat).mockImplementation(
      () =>
        new Promise((_, reject) => {
          rejectRename = reject
        }),
    )
    await render()
    expect(host.textContent).toContain("Old title")
    const renameButton = [...host.querySelectorAll("button")].find((button) => button.textContent === "rename")
    await act(async () => {
      renameButton?.click()
      await new Promise((resolve) => setTimeout(resolve, 0))
    })
    expect(host.textContent).toContain("New title")
    await act(async () => {
      rejectRename(new Error("Chat storage is not configured."))
      await new Promise((resolve) => setTimeout(resolve, 0))
    })
    expect(host.textContent).toContain("Old title")
    expect(host.textContent).not.toContain("New title")
    expect(host.textContent).toContain("Chat storage is not configured.")
  })

  it("removes a chat after delete resolves", async () => {
    await render()
    const remove = [...host.querySelectorAll("button")].find((button) => button.textContent === "remove")
    await act(async () => {
      remove?.click()
    })
    for (let attempt = 0; attempt < 20 && host.textContent?.includes("Old title"); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0))
      })
    }
    expect(deleteChat).toHaveBeenCalledWith("session-1", "c1")
    expect(host.textContent).not.toContain("Old title")
  })
})
