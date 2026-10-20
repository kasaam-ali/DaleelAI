/** PR 1: the disclaimer sits under the input, and Send is at full action colour at rest. */

// @vitest-environment happy-dom
Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
import { act } from "react"
import { createRoot } from "react-dom/client"
import { describe, expect, it } from "vitest"
import Composer from "./Composer"

describe("Composer disclaimer", () => {
  it("shows the short disclaimer once and keeps Send unfaded when empty", () => {
    const host = document.createElement("div")
    document.body.append(host)
    const root = createRoot(host)
    act(() => {
      root.render(
        <Composer value="" busy={false} error={null} preview={null} copy={(key) => key} onChange={() => undefined} onSubmit={() => undefined} onStop={() => undefined} />,
      )
    })
    expect(host.textContent?.split("disclaimerShort").length).toBe(2)
    const send = host.querySelector('button[aria-label="send"]')
    expect(send?.className).toContain("bg-seal")
    expect(send?.className).not.toContain("opacity")
    act(() => root.unmount())
    host.remove()
  })
})
