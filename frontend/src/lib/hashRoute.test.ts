/** Checks hash routes, including a copied chat link. */

import { describe, expect, it } from "vitest"
import { parseHash } from "./hashRoute"

const ID = "6f1c2a40-7b0e-4a1d-9c3e-1a2b3c4d5e6f"

describe("parseHash", () => {
  it("opens home when the hash is empty", () => {
    expect(parseHash("")).toEqual({ view: "home", chatId: null })
  })

  it("reads a plain page", () => {
    expect(parseHash("#/calculator")).toEqual({ view: "calculator", chatId: null })
  })

  it("reads a chat id from a copied link", () => {
    expect(parseHash(`#/chat/${ID}`)).toEqual({ view: "chat", chatId: ID })
  })

  it("ignores a chat path that is not a uuid", () => {
    expect(parseHash("#/chat/notes")).toEqual({ view: "chat", chatId: null })
  })
})
