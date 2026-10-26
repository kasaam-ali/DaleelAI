/** Checks the SSE parser and the chat rename/delete calls. */

import { afterEach, describe, expect, it, vi } from "vitest"
import { deleteChat, parseSseBlock, renameChat, takeSseEvents } from "./chat"

describe("SSE parser", () => {
  it("reads a meta event", () => {
    const event = parseSseBlock(
      'event: meta\ndata: {"chat_id":"c","message_id":"m","intent":"qa","language":"en","tax_year":"TY2027"}',
    )
    expect(event?.event).toBe("meta")
    if (event?.event === "meta") expect(event.data.tax_year).toBe("TY2027")
  })

  it("splits a buffer and keeps a partial tail", () => {
    const buffer = 'event: token\ndata: {"text":"Tax"}\n\nevent: token\ndata: {"text":" due"}'
    const taken = takeSseEvents(buffer)
    expect(taken.events).toHaveLength(1)
    expect(taken.events[0]?.event).toBe("token")
    expect(taken.rest.startsWith("event: token")).toBe(true)
  })

  it("accepts CRLF frames", () => {
    const taken = takeSseEvents('event: done\r\ndata: {}\r\n\r\n')
    expect(taken.events.map((event) => event.event)).toEqual(["done"])
  })
})

describe("chat rename and delete", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("sends a PATCH title", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(JSON.stringify({ id: "chat-1", title: "Salary", created_at: "a", updated_at: "b" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    )
    vi.stubGlobal("fetch", fetchMock)
    const row = await renameChat("session-1", "chat-1", "Salary")
    expect(row.title).toBe("Salary")
    const call = fetchMock.mock.calls[0]
    if (!call) throw new Error("missing fetch call")
    expect(String(call[0])).toContain("/api/v1/chats/chat-1")
    const init = call[1] as RequestInit
    expect(init.method).toBe("PATCH")
    expect(init.body).toBe(JSON.stringify({ title: "Salary" }))
    expect((init.headers as Record<string, string>)["X-Session-Id"]).toBe("session-1")
  })

  it("treats delete 204 and 404 as success", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }))
    vi.stubGlobal("fetch", fetchMock)
    await expect(deleteChat("session-1", "chat-1")).resolves.toBeUndefined()
    const deleted = fetchMock.mock.calls[0]
    if (!deleted) throw new Error("missing fetch call")
    expect((deleted[1] as RequestInit).method).toBe("DELETE")
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: "That chat was not found." } }), { status: 404 }))
    await expect(deleteChat("session-1", "chat-1")).resolves.toBeUndefined()
  })

  it("shows the server message when delete fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ error: { code: "repository_unavailable", message: "Chat storage is not configured." } }), {
            status: 503,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    )
    await expect(deleteChat("session-1", "chat-1")).rejects.toThrow("Chat storage is not configured.")
  })
})
