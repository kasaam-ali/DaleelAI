/** Checks that changing one profile field does not clear the others. */

import { describe, expect, it } from "vitest"
import {
  CHAT_KEY,
  EMPTY_PROFILE,
  PROFILE_KEY,
  SESSION_KEY,
  clearLocalHistory,
  readProfile,
  readSessionId,
  sanitizeProfile,
  writeProfile,
  type StorageLike,
} from "./session"

function memory(): StorageLike & { data: Map<string, string> } {
  const data = new Map<string, string>()
  return {
    data,
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => {
      data.set(key, value)
    },
    removeItem: (key) => {
      data.delete(key)
    },
  }
}

describe("session", () => {
  it("creates one session id and reuses it", () => {
    const store = memory()
    const first = readSessionId(store)
    const second = readSessionId(store)
    expect(first).toBe(second)
    expect(store.data.get(SESSION_KEY)).toBe(first)
    expect(first).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    )
  })

  it("keeps earlier answers when a later field is set", () => {
    const current = sanitizeProfile({ taxpayer_type: "freelancer" })
    expect(sanitizeProfile({ ...current, province: "sindh" })).toEqual({
      taxpayer_type: "freelancer",
      filer_status: null,
      province: "sindh",
    })
  })

  it("drops unknown profile values", () => {
    expect(sanitizeProfile({ taxpayer_type: "freelancer", filer_status: "maybe", province: "sindh" })).toEqual({
      taxpayer_type: "freelancer",
      filer_status: null,
      province: "sindh",
    })
  })

  it("replaces the session and drops the open chat", () => {
    const store = memory()
    const first = readSessionId(store)
    store.setItem(CHAT_KEY, "chat-1")
    const next = clearLocalHistory(store)
    expect(next).not.toBe(first)
    expect(store.data.get(SESSION_KEY)).toBe(next)
    expect(store.data.has(CHAT_KEY)).toBe(false)
  })

  it("round-trips a profile and ignores broken JSON", () => {
    const store = memory()
    writeProfile(store, { taxpayer_type: "salaried", filer_status: "filer", province: "punjab" })
    expect(readProfile(store).taxpayer_type).toBe("salaried")
    store.data.set(PROFILE_KEY, "{")
    expect(readProfile(store)).toEqual(EMPTY_PROFILE)
  })
})
