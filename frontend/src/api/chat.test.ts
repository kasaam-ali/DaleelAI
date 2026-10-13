import { describe, expect, it } from "vitest"
import { parseSseBlock, takeSseEvents } from "./chat"

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
