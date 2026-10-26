/** Checks title rules, link shape, and search highlights. */

import { describe, expect, it } from "vitest"
import type { ChatSummary } from "../../api/chat"
import { assistantSnippet, chatHref, cleanTitle, searchChats } from "./chatText"

function chat(id: string, title: string, updated_at: string): ChatSummary {
  return { id, title, created_at: updated_at, updated_at }
}

describe("chat text", () => {
  it("accepts a trimmed title of 1 to 80 characters", () => {
    expect(cleanTitle("  Salary tax  ")).toBe("Salary tax")
    expect(cleanTitle("")).toBeNull()
    expect(cleanTitle("   ")).toBeNull()
    expect(cleanTitle("a\nb")).toBeNull()
    expect(cleanTitle("x".repeat(81))).toBeNull()
  })

  it("builds a hash link for one chat", () => {
    expect(chatHref("abc", "https://daleel.example/app?lang=en")).toBe("https://daleel.example/app?lang=en#/chat/abc")
  })

  it("uses the latest assistant text as the snippet", () => {
    expect(
      assistantSnippet([
        { role: "user", content: "question" },
        { role: "assistant", content: "First answer" },
        { role: "assistant", content: "  Later   answer  " },
      ]),
    ).toBe("Later answer")
  })

  it("matches a title or a snippet and marks the hit", () => {
    const chats = [
      chat("1", "Freelancer income tax", "2026-10-19T00:00:00Z"),
      chat("2", "Crypto notes", "2026-10-18T00:00:00Z"),
      chat("3", "Salary for TY2026", "2026-10-17T00:00:00Z"),
    ]
    const hits = searchChats(chats, { "2": "The bank deducts tax at a fixed rate" }, "tax")
    expect(hits.map((hit) => hit.chat.id)).toEqual(["1", "2"])
    expect(hits[0]?.titleRanges).toEqual([{ start: 18, end: 21 }])
    expect(hits[1]?.snippetRanges).toEqual([{ start: 17, end: 20 }])
  })

  it("returns every chat when the query is empty", () => {
    const chats = [chat("a", "One", "2026-10-01T00:00:00Z"), chat("b", "Two", "2026-10-02T00:00:00Z")]
    expect(searchChats(chats, {}, "  ").map((hit) => hit.chat.id)).toEqual(["b", "a"])
  })
})
