/** Tilt is capped at 6° and only on fine pointers; reduced motion renders the final state with no JS motion. */

// @vitest-environment happy-dom
import { act, useRef } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { t, type CopyKey } from "../../i18n"
import HomePage from "./HomePage"
import { launchFromCard, tunedEyebrow } from "./filing"
import { MAX_TILT, tiltFor, useTilt } from "./useTilt"

const copy = (key: CopyKey) => t("en", key)

function mockMedia(matches: Record<string, boolean>) {
  window.matchMedia = vi.fn((query: string) => ({
    matches: matches[query] ?? false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
}

let root: Root
let host: HTMLDivElement
const realMatchMedia = window.matchMedia

beforeEach(() => {
  host = document.createElement("div")
  document.body.append(host)
  root = createRoot(host)
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
    cb(0)
    return 1
  })
})
afterEach(() => {
  act(() => root.unmount())
  host.remove()
  window.matchMedia = realMatchMedia
  vi.unstubAllGlobals()
})

function Card() {
  const card = useRef<HTMLDivElement>(null)
  const inner = useRef<HTMLDivElement>(null)
  useTilt(card, inner)
  return (
    <div ref={card} data-testid="card">
      <div ref={inner} data-testid="inner" />
    </div>
  )
}

function move() {
  const card = host.querySelector<HTMLElement>('[data-testid="card"]')!
  card.getBoundingClientRect = () => ({ left: 0, top: 0, width: 100, height: 100, right: 100, bottom: 100, x: 0, y: 0, toJSON: () => ({}) })
  act(() => card.dispatchEvent(new PointerEvent("pointermove", { clientX: 100, clientY: 0, bubbles: true })))
  return host.querySelector<HTMLElement>('[data-testid="inner"]')!.style.transform
}

describe("tilt", () => {
  it("never passes 6 degrees", () => {
    expect(MAX_TILT).toBe(6)
    for (const [x, y] of [[0, 0], [1, 1], [-5, 9], [0.5, 0.5]]) {
      const { rotateX, rotateY } = tiltFor(x, y)
      expect(Math.abs(rotateX)).toBeLessThanOrEqual(6)
      expect(Math.abs(rotateY)).toBeLessThanOrEqual(6)
    }
  })

  it("tilts on a fine pointer", () => {
    mockMedia({ "(pointer: fine)": true })
    act(() => root.render(<Card />))
    expect(move()).toBe("perspective(900px) rotateX(6.00deg) rotateY(6.00deg) translateZ(0)")
  })

  it("does nothing on a coarse pointer", () => {
    mockMedia({ "(pointer: fine)": false })
    act(() => root.render(<Card />))
    expect(move()).toBe("")
  })

  it("does nothing under reduced motion", () => {
    mockMedia({ "(pointer: fine)": true, "(prefers-reduced-motion: reduce)": true })
    act(() => root.render(<Card />))
    expect(move()).toBe("")
  })
})

describe("Home", () => {
  function renderHome(onOpen = vi.fn()) {
    act(() =>
      root.render(
        <main>
          <HomePage
            copy={copy}
            profile={{ taxpayer_type: null, filer_status: null, province: null }}
            taxYear="TY2026"
            taxYearSet={false}
            filingSaved={false}
            onProfile={vi.fn()}
            onTaxYear={vi.fn()}
            onFilingSaved={vi.fn()}
            onOpen={onOpen}
            onAsk={vi.fn()}
          />
        </main>,
      ),
    )
    return onOpen
  }

  it("shows exactly three tool cards, three chips and the trust row", () => {
    mockMedia({})
    renderHome()
    expect(Array.from(host.querySelectorAll(".tcard .tc-body b")).map((b) => b.childNodes[1]?.textContent)).toEqual([
      "Ask DaleelAI",
      "Tax calculator",
      "Notice samjho",
    ])
    expect(host.querySelectorAll(".hchip")).toHaveLength(3)
    expect(host.querySelectorAll(".trust3 > div")).toHaveLength(3)
    expect(host.querySelector('[data-testid="hero-emblem"]')?.getAttribute("aria-hidden")).toBe("true")
  })

  it("opens the tool at once under reduced motion (no launch layer)", () => {
    mockMedia({ "(prefers-reduced-motion: reduce)": true })
    const onOpen = renderHome()
    const card = host.querySelector<HTMLElement>('[data-art="calc"]')!
    act(() => card.click())
    expect(onOpen).toHaveBeenCalledWith("calculator")
    expect(document.querySelector(".launch-layer")).toBeNull()
  })

  it("grows a launch layer from the card, then routes after 520ms", () => {
    vi.useFakeTimers()
    mockMedia({})
    const onOpen = vi.fn()
    const main = document.createElement("main")
    const card = document.createElement("div")
    main.append(card)
    document.body.append(main)
    launchFromCard(card, onOpen)
    expect(document.querySelector(".launch-layer")).not.toBeNull()
    expect(onOpen).not.toHaveBeenCalled()
    vi.advanceTimersByTime(520)
    expect(onOpen).toHaveBeenCalledOnce()
    vi.advanceTimersByTime(300)
    expect(document.querySelector(".launch-layer")).toBeNull()
    main.remove()
    vi.useRealTimers()
  })

  it("opens a card with Enter", () => {
    mockMedia({ "(prefers-reduced-motion: reduce)": true })
    const onOpen = renderHome()
    const card = host.querySelector<HTMLElement>('[data-art="notice"]')!
    act(() => card.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })))
    expect(onOpen).toHaveBeenCalledWith("notice")
  })

  it("tunes the eyebrow to the saved details", () => {
    expect(tunedEyebrow({ taxpayer_type: "freelancer", filer_status: "filer", province: "punjab" }, "TY2026", copy)).toBe(
      "Tuned for a filer freelancer in Punjab · TY2026",
    )
  })
})
