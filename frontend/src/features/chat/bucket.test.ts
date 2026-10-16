import { describe, expect, it } from "vitest"
import { reduceBucket } from "./bucket"

describe("reduceBucket", () => {
  it("keeps the live answer when the chat id arrived before the token", () => {
    const current = {
      id: "chat-1",
      turns: [{ id: "local", draft: "" }],
    }
    const next = reduceBucket(
      current,
      (turns) => turns.map((turn) => (turn.id === "local" ? { ...turn, draft: "Tax Year" } : turn)),
      "chat-1",
      null,
    )
    expect(next.id).toBe("chat-1")
    expect(next.turns).toEqual([{ id: "local", draft: "Tax Year" }])
  })

  it("does not append a token onto a chat the user has left", () => {
    const next = reduceBucket(
      { id: "chat-1", turns: [{ id: "local", draft: "kept" }] },
      (turns) => turns.map((turn) => ({ ...turn, draft: `${turn.draft} more` })),
      "chat-2",
      null,
    )
    expect(next.turns).toEqual([])
  })
})