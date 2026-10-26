/** The shell status follows the browser and the health check. */

import { describe, expect, it } from "vitest"
import { serviceState } from "./health"

describe("serviceState", () => {
  it("is offline while the browser has no connection, even after a healthy response", () => {
    expect(serviceState(false, { error: false, ok: true })).toBe("offline")
  })

  it("is degraded when the browser is online and the health check failed", () => {
    expect(serviceState(true, { error: true, ok: false })).toBe("degraded")
  })

  it("is online only when the browser is online and the health check succeeded", () => {
    expect(serviceState(true, { error: false, ok: true })).toBe("online")
    expect(serviceState(true, { error: false, ok: false })).toBe("checking")
  })
})
