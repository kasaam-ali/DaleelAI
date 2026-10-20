/** PR 3 shell + Nav v2: ToolsNav vs ChatSidebar per route, a persisted rail, the filing row + popover, and the §11.3 a11y fixes. */

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
  it("tool routes show exactly the 6 ToolsNav links in order, the parent marked current, and no chat controls", () => {
    const cases: [Parameters<typeof AppShell>[0]["view"], string][] = [
      ["home", "Home"],
      ["calculator", "Tax Calculator"],
      ["filer", "Tax Calculator"],
      ["notice", "Notice"],
      ["experts", "Notice"],
      ["checklist", "Checklists"],
      ["privacy", "About & settings"],
      ["updates", "About & settings"],
      ["evaluation", "About & settings"],
    ]
    for (const [view, active] of cases) {
      render({ view })
      const links = Array.from(host.querySelectorAll<HTMLAnchorElement>("[data-tools-nav] a.nav-item"))
      expect(links.map((a) => a.querySelector(".lbl")?.textContent)).toEqual([
        "Home",
        "Ask Daleel",
        "Tax Calculator",
        "Notice",
        "Checklists",
        "About & settings",
      ])
      expect(links.map((a) => a.getAttribute("href"))).toEqual(["#/", "#/chat/new", "#/calculator", "#/notice", "#/checklists", "#/about"])
      const current = host.querySelectorAll('[aria-current="page"]')
      expect(current).toHaveLength(1)
      expect(current[0].textContent).toContain(active)
      expect(host.querySelector("[data-new-chat]")).toBeNull()
      expect(host.querySelector("[data-search-chats]")).toBeNull()
      expect(host.querySelector("[data-tool-row]")).toBeNull()
      expect(host.querySelector("[data-brand-home]")).toBeNull()
      expect(host.textContent).not.toContain(copy("recentsLabel"))
      expect(host.querySelector("[data-filing-row]")).not.toBeNull()
      expect(host.querySelector("[data-status]")).not.toBeNull()
    }
  })

  it("chat route shows the ChatSidebar: brand link home, 5-icon Tools row, New chat, Search, history; no ToolsNav", () => {
    const props = render({ view: "chat" })
    expect(host.querySelector("[data-tools-nav]")).toBeNull()
    const brand = host.querySelector<HTMLAnchorElement>("[data-brand-home]")!
    expect(brand.getAttribute("href")).toBe("#/")
    expect(brand.getAttribute("title")).toBe("Back to Home")
    expect(brand.hasAttribute("aria-label")).toBe(false)
    expect(brand.textContent).toBe("DaleelAI" + copy("subtitle") + " · Back to Home")
    const icons = Array.from(host.querySelectorAll<HTMLAnchorElement>("[data-tool-row] a.tr-btn"))
    expect(icons.map((a) => a.getAttribute("aria-label"))).toEqual(["Home", "Tax Calculator", "Notice", "Checklists", "About & settings"])
    expect(icons.map((a) => a.getAttribute("href"))).toEqual(["#/", "#/calculator", "#/notice", "#/checklists", "#/about"])
    expect(host.querySelector("[data-new-chat]")).not.toBeNull()
    expect(host.querySelector("[data-search-chats]")).not.toBeNull()
    expect(host.textContent).toContain("Your chats will show here")
    act(() => icons[3].click())
    expect(props.onView).toHaveBeenCalledWith("checklist")
    act(() => brand.click())
    expect(props.onView).toHaveBeenCalledWith("home")
    act(() => host.querySelector<HTMLButtonElement>("[data-new-chat]")!.click())
    expect(props.onNewChat).toHaveBeenCalledOnce()
  })

  it("Ask Daleel opens a new chat; other links route in-app", () => {
    const props = render()
    const link = (label: string) => Array.from(host.querySelectorAll<HTMLAnchorElement>("[data-tools-nav] a")).find((a) => a.textContent?.includes(label))!
    act(() => link("Ask Daleel").click())
    expect(props.onNewChat).toHaveBeenCalledOnce()
    act(() => link("About & settings").click())
    expect(props.onView).toHaveBeenCalledWith("privacy")
    act(() => host.querySelector<HTMLButtonElement>("[data-status]")!.click())
    expect(props.onView).toHaveBeenLastCalledWith("privacy")
  })

  it("keeps the rail across a reload, and its short labels are aria-hidden", () => {
    render()
    const collapse = host.querySelector<HTMLButtonElement>(".sb-collapse")!
    act(() => collapse.click())
    expect(host.querySelector("aside")?.getAttribute("data-rail")).toBe("true")
    expect(RAIL_KEY).toBe("daleelai.rail")
    expect(localStorage.getItem(RAIL_KEY)).toBe("1")
    act(() => root.unmount())
    root = createRoot(host)
    render()
    expect(host.querySelector("aside")?.getAttribute("data-rail")).toBe("true")
    const shorts = Array.from(host.querySelectorAll(".nav-item .short"))
    expect(shorts.map((item) => item.textContent)).toEqual(["Home", "Ask", "Calc", "Notice", "Lists", "About"])
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
