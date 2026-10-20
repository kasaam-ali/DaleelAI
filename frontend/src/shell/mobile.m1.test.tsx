/** PR M1 (SPEC §10.1): phone filing chip → bottom sheet, dismissible disclaimer, phone-only top bar rules, no desktop change. */

// @vitest-environment happy-dom
import { act, useState } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import HomePage from "../features/home/HomePage"
import { t, type CopyKey } from "../i18n"
import type { ClientTaxYear, Profile, UiLanguage } from "../lib/session"
import AppShell from "./AppShell"
import { DISC_KEY } from "./mobile"

const realMatchMedia = window.matchMedia
function viewport(phone: boolean) {
  window.matchMedia = vi.fn((query: string) => ({
    matches: query.includes("max-width: 767px") ? phone : false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  })) as unknown as typeof window.matchMedia
}

let root: Root
let host: HTMLDivElement
beforeEach(() => {
  sessionStorage.clear()
  localStorage.clear()
  host = document.createElement("div")
  document.body.append(host)
  root = createRoot(host)
})
afterEach(() => {
  act(() => root.unmount())
  host.remove()
  window.matchMedia = realMatchMedia
})

function Home({ language = "en", initial, saved: savedInit = false }: { language?: UiLanguage; initial: Profile; saved?: boolean }) {
  const copy = (key: CopyKey) => t(language, key)
  const [profile, setProfile] = useState(initial)
  const [taxYear, setTaxYear] = useState<ClientTaxYear>("TY2026")
  const [taxYearSet, setTaxYearSet] = useState(savedInit)
  const [saved, setSaved] = useState(savedInit)
  return (
    <HomePage
      copy={copy}
      profile={profile}
      taxYear={taxYear}
      taxYearSet={taxYearSet}
      filingSaved={saved}
      onProfile={(patch) => setProfile((p) => ({ ...p, ...patch }))}
      onTaxYear={(y) => {
        setTaxYear(y)
        setTaxYearSet(true)
      }}
      onFilingSaved={setSaved}
      onOpen={() => undefined}
      onAsk={() => undefined}
    />
  )
}

const empty: Profile = { taxpayer_type: null, filer_status: null, province: null }
const full: Profile = { taxpayer_type: "freelancer", filer_status: "filer", province: "punjab" }

describe("Home on phones (M1)", () => {
  it("shows the filing chip instead of the inline step, and the chip opens a modal bottom sheet", () => {
    viewport(true)
    act(() => root.render(<Home initial={empty} />))
    expect(host.querySelector(".phome > .fstep")).toBeNull()
    const chip = host.querySelector<HTMLButtonElement>("[data-filing-chip]")!
    expect(chip.getAttribute("aria-haspopup")).toBe("dialog")
    expect(chip.textContent).toContain("Filing details")
    expect(chip.textContent).toContain("Not set yet")
    expect(chip.querySelectorAll(".fc-dots i")).toHaveLength(4)

    act(() => chip.click())
    const sheet = host.querySelector('[role="dialog"][aria-modal="true"].m-sheet')!
    expect(sheet).not.toBeNull()
    expect(sheet.querySelector("h2")?.textContent).toBe("Enter your filing details")
    expect(sheet.querySelector(".fstep.in-sheet")).not.toBeNull()
    expect(sheet.querySelector(".grab")).not.toBeNull()
    expect(sheet.contains(document.activeElement)).toBe(true)

    // pick values in the sheet; the chip mirrors them
    const radio = (label: string) => Array.from(sheet.querySelectorAll<HTMLButtonElement>('[role="radio"]')).find((b) => b.textContent === label)!
    act(() => radio("Non-filer").click())
    expect(chip.textContent).toContain("1 of 4 set")

    act(() => {
      document.activeElement!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))
    })
    expect(host.querySelector(".m-sheet")).toBeNull()
  })

  it("filled: the chip shows the summary and the sheet shows the values with Edit", () => {
    viewport(true)
    act(() => root.render(<Home initial={full} saved />))
    const chip = host.querySelector<HTMLButtonElement>("[data-filing-chip]")!
    expect(chip.className).toContain("ok")
    expect(chip.textContent).toContain("Freelancer · Filer · Punjab · TY2026")
    expect(chip.querySelector(".fc-dots")).toBeNull()
    act(() => chip.click())
    const sheet = host.querySelector(".m-sheet")!
    expect(sheet.querySelector("h2")?.textContent).toBe("Filing details")
    expect(sheet.querySelectorAll(".pill")).toHaveLength(4)
    expect(sheet.textContent).toContain("Sent with every question")
    act(() => sheet.querySelector<HTMLButtonElement>("[data-sheet-close]")!.click())
    expect(host.querySelector(".m-sheet")).toBeNull()
  })

  it("Roman Urdu chip copy", () => {
    viewport(true)
    act(() => root.render(<Home language="roman_urdu" initial={empty} />))
    expect(host.querySelector("[data-filing-chip]")?.textContent).toContain("Abhi set nahi")
  })

  it("desktop keeps the inline filing step and no chip", () => {
    viewport(false)
    act(() => root.render(<Home initial={empty} />))
    expect(host.querySelector("[data-filing-chip]")).toBeNull()
    expect(host.querySelector(".phome > .fstep")).not.toBeNull()
  })
})

describe("Shell disclaimer banner (M1)", () => {
  function shell(language: UiLanguage = "en") {
    const copy = (key: CopyKey) => t(language, key)
    act(() =>
      root.render(
        <AppShell
          view="home"
          language={language}
          theme="light"
          profile={empty}
          taxYear="TY2026"
          taxYearSet={false}
          filingSaved={false}
          chats={[]}
          snippets={{}}
          activeChatId={null}
          service="online"
          menuOpen={false}
          copy={copy}
          onView={vi.fn()}
          onNewChat={vi.fn()}
          onSelectChat={vi.fn()}
          onRename={vi.fn(async () => undefined)}
          onDelete={vi.fn(async () => undefined)}
          onPrefetchSnippets={vi.fn()}
          onLanguage={vi.fn()}
          onTheme={vi.fn()}
          onProfile={vi.fn()}
          onTaxYear={vi.fn()}
          onClearFiling={vi.fn()}
          onMenu={vi.fn()}
        >
          <p>page</p>
        </AppShell>,
      ),
    )
  }

  for (const language of ["en", "roman_urdu"] as const) {
    it(`✕ hides it for the session and shows the toast (${language})`, () => {
      shell(language)
      const banner = host.querySelector("[data-mobile-disclaimer]")!
      expect(banner.textContent).toContain(t(language, "disclaimerShort"))
      const x = banner.querySelector("button")!
      expect(x.getAttribute("aria-label")).toBe(language === "en" ? "Close" : "Band karein")
      act(() => x.click())
      expect(host.querySelector("[data-mobile-disclaimer]")).toBeNull()
      expect(sessionStorage.getItem(DISC_KEY)).toBe("1")
      expect(host.textContent).toContain(
        language === "en" ? "Disclaimer hidden. It still shows under every answer." : "Disclaimer chhupa diya. Har jawab ke neeche yeh likha rehta hai.",
      )
      act(() => root.unmount())
      root = createRoot(host)
      shell(language)
      expect(host.querySelector("[data-mobile-disclaimer]")).toBeNull()
    })
  }
})
