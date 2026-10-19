/** Pure checks for the loading, error, and refusal states. */

import { describe, expect, it } from "vitest"
import { canAutoRetry, chipLabel, retryDelayMs, type TurnError } from "./failure"
import { refusalKind } from "./refusal"
import { PENDING_PHASES, reducePhases } from "./steps"

const busy: TurnError = { status: 503, code: "providers_busy", message: "All AI providers are busy right now." }

describe("chat states", () => {
  it("labels a 503 and only auto-retries 429 and 503", () => {
    expect(chipLabel(busy)).toBe("503 · Providers busy")
    expect(chipLabel({ status: 429, code: "rate_limited", message: "slow down" })).toBe("429 · Too many requests")
    expect(chipLabel({ status: null, code: "qa_failed", message: "no" })).toBe("qa_failed")
    expect(canAutoRetry(busy)).toBe(true)
    expect(canAutoRetry({ status: 429, code: "rate_limited", message: "slow down" })).toBe(true)
    expect(canAutoRetry({ status: null, code: "qa_failed", message: "no" })).toBe(false)
    expect(retryDelayMs(0)).toBe(20_000)
    expect(retryDelayMs(1)).toBe(40_000)
    expect(retryDelayMs(2)).toBe(80_000)
    expect(retryDelayMs(3)).toBeNull()
  })

  it("maps each limit onto its card", () => {
    expect(refusalKind("qa", "none")).toBe("evidence")
    expect(refusalKind("qa", "none", "demo-cache")).toBeNull()
    expect(refusalKind("out_of_scope", "verified")).toBe("scope")
    expect(refusalKind("chitchat", "none")).toBe("scope")
    expect(refusalKind("refuse", "none")).toBe("declined")
    expect(refusalKind("provincial", "none")).toBe("provincial")
    expect(refusalKind("qa", "verified")).toBeNull()
  })

  it("advances the four loading steps", () => {
    const searching = reducePhases(PENDING_PHASES, "retrieve", "start")
    expect(searching).toEqual(["done", "active", "pending", "pending"])
    const writing = reducePhases(searching, "generate", "start")
    expect(writing).toEqual(["done", "done", "active", "pending"])
    expect(reducePhases(writing, "generate", "end")[2]).toBe("done")
  })
})
