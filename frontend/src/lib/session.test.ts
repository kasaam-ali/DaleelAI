/** Checks that changing one profile field does not clear the others. */

import { describe, expect, it } from "vitest"
import {
  CHAT_KEY,
  CORPUS_DATES_KEY,
  EMPTY_PROFILE,
  PROFILE_KEY,
  SESSION_KEY,
  clearLocalHistory,
  currentTaxYear,
  readAnswerLanguage,
  readCorpusDates,
  readLanguage,
  readOfflineQueue,
  readProfile,
  readSessionId,
  readTaxYear,
  rememberCorpusDate,
  sanitizeProfile,
  writeAnswerLanguage,
  writeLanguage,
  writeOfflineQueue,
  writeProfile,
  writeTaxYear,
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
    expect(store.data.has(CORPUS_DATES_KEY)).toBe(false)
  })

  it("remembers a law-as-of date for a saved answer", () => {
    const store = memory()
    rememberCorpusDate(store, "message-1", "2026-10-14")
    expect(readCorpusDates(store)).toEqual({ "message-1": "2026-10-14" })
    store.setItem(CORPUS_DATES_KEY, "2026-10-14")
    clearLocalHistory(store)
    expect(readCorpusDates(store)).toEqual({})
  })

  it("keeps the shell language and the per-chat answer language apart", () => {
    const store = memory()
    expect(readLanguage(store)).toBe("en")
    writeLanguage(store, "roman_urdu")
    expect(readLanguage(store)).toBe("roman_urdu")
    expect(readAnswerLanguage(store, null)).toBe("auto")
    writeAnswerLanguage(store, "chat-1", "en")
    writeAnswerLanguage(store, "chat-2", "roman_urdu")
    expect(readAnswerLanguage(store, "chat-1")).toBe("en")
    expect(readAnswerLanguage(store, "chat-2")).toBe("roman_urdu")
    expect(readLanguage(store)).toBe("roman_urdu")
  })

  it("keeps an offline question until it is sent", () => {
    const store = memory()
    expect(readOfflineQueue(store)).toEqual([])
    writeOfflineQueue(store, [
      { id: "q-1", text: "Section 149?" },
      { id: "q-2", text: "  " },
    ])
    expect(readOfflineQueue(store)).toEqual([{ id: "q-1", text: "Section 149?" }])
    writeOfflineQueue(store, [])
    expect(store.data.has("daleelai.offline_queue")).toBe(false)
    store.data.set("daleelai.offline_queue", "{")
    expect(readOfflineQueue(store)).toEqual([])
  })

  it("round-trips a profile and ignores broken JSON", () => {
    const store = memory()
    writeProfile(store, { taxpayer_type: "salaried", filer_status: "filer", province: "punjab" })
    expect(readProfile(store).taxpayer_type).toBe("salaried")
    store.data.set(PROFILE_KEY, "{")
    expect(readProfile(store)).toEqual(EMPTY_PROFILE)
  })

  it("uses the Karachi tax year and keeps a saved choice", () => {
    expect(currentTaxYear(new Date("2026-06-30T18:00:00Z"))).toBe("TY2026")
    expect(currentTaxYear(new Date("2026-06-30T19:30:00Z"))).toBe("TY2027")
    expect(currentTaxYear(new Date("2026-10-19T08:00:00Z"))).toBe("TY2027")
    const store = memory()
    expect(readTaxYear(store, new Date("2026-10-19T08:00:00Z"))).toBe("TY2027")
    writeTaxYear(store, "TY2026")
    expect(readTaxYear(store, new Date("2026-10-19T08:00:00Z"))).toBe("TY2026")
  })
})
