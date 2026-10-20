/** PR 3 shell: four nav items, a persisted rail, the filing row + popover, and the §11.3 a11y fixes. */

// @vitest-environment happy-dom
import { act } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { t, type CopyKey } from "../i18n"
import { RAIL_KEY, type Profile } from "../lib/session"
import AppShell from "./AppShell"

const copy = (key: CopyKey) => t("en", key)
const empty: Profile = { taxpayer_type: null, filer_status: null, province: null }

let root: Root
let host: HTMLDivElement

function render(overrides: Partial<Parameters<typeof AppShell>[0]> = {}) {
  const props: Parameters<typeof AppShell>[0] = {
    view: "home",
    language: "en",
    theme: "light",
    profile: empty,
    taxYear: "TY2026",
    taxYearSet: false,
    filingSaved: false,
    chats: [],
    snippets: {},
    activeChatId: null,
    service: "online",
    menuOpen: false,
    copy,
    onView: vi.fn(),
    onNewChat: vi.fn(),
    onSelectChat: vi.fn(),
    onRename: vi.fn(async () => undefined),
    onDelete: vi.fn(async () => undefined),
    onPrefetchSnippets: vi.fn(),
    onLanguage: vi.fn(),
    onTheme: vi.fn(),
    onProfile: vi.fn(),
    onTaxYear: vi.fn(),
    onClearFiling: vi.fn(),
    onMenu: vi.fn(),
    children: <p>page</p>,
    ...overrides,
  }
  act(() => root.render(<AppShell {...props} />))
  return props
}

beforeEach(() => {
  localStorage.clear()
  host = document.createElement("div")
  document.body.append(host)
  root = createRoot(host)
})

afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

describe("AppShell (PR 3)", () => {
  it("has exactly four main nav items, with aria-current on the open page", () => {
    render({ view: "calculator" })
    const items = Array.from(host.querySelectorAll("nav .nav-item")).map((item) => item.querySelector(".lbl")?.textContent)
    expect(items).toEqual(["Home", "Sawal poocho", "Tax calculator", "Notice samjho"])
    const current = host.querySelectorAll('[aria-current="page"]')
    expect(current).toHaveLength(1)
    expect(current[0].textContent).toContain("Tax calculator")
    expect(host.textContent).not.toContain(copy("navUpdates"))
    expect(host.textContent).not.toContain(copy("navEvaluation"))
    expect(host.textContent).toContain("About & settings")
  })

  it("keeps the rail across a reload, and its short labels are aria-hidden", () => {
    render()
    const collapse = host.querySelector<HTMLButtonElement>(".sb-collapse")!
    act(() => collapse.click())
    expect(host.querySelector("aside")?.getAttribute("data-rail")).toBe("true")
    expect(localStorage.getItem(RAIL_KEY)).toBe("1")
    act(() => root.unmount())
    root = createRoot(host)
    render()
    expect(host.querySelector("aside")?.getAttribute("data-rail")).toBe("true")
    const shorts = Array.from(host.querySelectorAll(".nav-item .short"))
    expect(shorts.map((item) => item.textContent)).toEqual(["Home", "Ask", "Calc", "Notice", "About"])
    for (const item of shorts) expect(item.getAttribute("aria-hidden")).toBe("true")
  })

  it("puts Skip to content first and names the theme toggle with aria-pressed", () => {
    const props = render({ theme: "dark" })
    const first = host.querySelector("a, button")
    expect(first?.textContent).toBe("Skip to content")
    expect(first?.getAttribute("href")).toBe("#main")
    const toggle = host.querySelector<HTMLButtonElement>('button[aria-label="Dark theme"]')!
    expect(toggle.getAttribute("aria-pressed")).toBe("true")
    act(() => toggle.click())
    expect(props.onTheme).toHaveBeenCalledOnce()
  })

  it("mirrors the filing state in the sidebar row", () => {
    render()
    const summary = () => host.querySelector("[data-filing-summary]")?.textContent
    expect(summary()).toBe("Not set yet")
    render({ profile: { taxpayer_type: "freelancer", filer_status: "filer", province: null } })
    expect(summary()).toBe("2 of 4 set")
    render({ profile: { taxpayer_type: "freelancer", filer_status: "filer", province: "punjab" }, taxYearSet: true, filingSaved: true })
    expect(summary()).toBe("Freelancer · Filer · Punjab · TY2026")
  })

  it("opens the filing popover from the row, edits a field, and closes on Escape with focus back on the row", () => {
    const props = render()
    const row = host.querySelector<HTMLButtonElement>("[data-filing-row]")!
    act(() => {
      row.focus()
      row.click()
    })
    const pop = host.querySelector('[role="dialog"]')
    expect(pop?.getAttribute("aria-label")).toBe("Filing details")
    expect(document.activeElement?.id).toBe("fp-taxpayer")
    // useModal: the rest of the page is inert while the dialog is open.
    const column = host.querySelector("main")!.parentElement as HTMLElement
    expect(column.inert).toBe(true)
    const select = host.querySelector<HTMLSelectElement>("#fp-filer")!
    act(() => {
      select.value = "non_filer"
      select.dispatchEvent(new Event("change", { bubbles: true }))
    })
    expect(props.onProfile).toHaveBeenCalledWith({ filer_status: "non_filer" })
    act(() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })))
    expect(host.querySelector('[role="dialog"]')).toBeNull()
    expect(document.activeElement).toBe(row)
    expect(column.inert).toBe(false)
  })
})
