/** Your data: Clear chats lists what it clears and asks first, with the safe button focused. */

// @vitest-environment happy-dom
import { act } from "react"
import { createRoot } from "react-dom/client"
import { describe, expect, it, vi } from "vitest"
import { t, type CopyKey } from "../../i18n"
import PrivacyPage from "./PrivacyPage"

describe("PrivacyPage · Your data", () => {
  for (const language of ["en", "roman_urdu"] as const) {
    it(`asks before clearing chats (${language})`, () => {
      const copy = (key: CopyKey) => t(language, key)
      const onClear = vi.fn()
      const host = document.createElement("div")
      document.body.append(host)
      const root = createRoot(host)
      act(() => root.render(<PrivacyPage copy={copy} onClearHistory={onClear} />))
      const section = host.querySelector('section[aria-labelledby="your-data"]')!
      expect(section.querySelector("h3")?.textContent).toBe(copy("dataTitle"))
      expect(section.textContent).toContain(copy("dataClearBody"))
      expect(Array.from(section.querySelectorAll("li")).map((li) => li.textContent)).toEqual([copy("dataClearWhat1"), copy("dataClearWhat2")])

      act(() => host.querySelector<HTMLButtonElement>("[data-clear-history]")!.click())
      const dialog = host.querySelector('[role="alertdialog"]')!
      expect(dialog.textContent).toContain(copy("dataDlgTitle"))
      expect(dialog.textContent).toContain(copy("dataDlgNote"))
      expect(document.activeElement?.textContent).toBe(copy("dataDlgCancel"))
      expect(onClear).not.toHaveBeenCalled()

      const buttons = Array.from(dialog.querySelectorAll<HTMLButtonElement>("button"))
      expect(buttons.map((b) => b.textContent)).toEqual([copy("dataDlgCancel"), copy("dataDlgConfirm")])
      expect(buttons[0].textContent).toBe(language === "en" ? "Keep them" : "Rehne dein")
      expect(buttons[1].textContent).toBe(language === "en" ? "Clear chats" : "Chats saaf karein")
      expect(buttons[1].className).toContain("bg-error")
      expect(buttons[1].hasAttribute("data-destructive")).toBe(true)

      // Esc does what the safe button does.
      act(() => {
        document.activeElement!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))
      })
      expect(host.querySelector('[role="alertdialog"]')).toBeNull()
      expect(onClear).not.toHaveBeenCalled()

      act(() => host.querySelector<HTMLButtonElement>("[data-clear-history]")!.click())
      act(() => (document.activeElement as HTMLButtonElement).click())
      expect(host.querySelector('[role="alertdialog"]')).toBeNull()
      expect(onClear).not.toHaveBeenCalled()

      act(() => host.querySelector<HTMLButtonElement>("[data-clear-history]")!.click())
      const confirm = Array.from(host.querySelectorAll<HTMLButtonElement>('[role="alertdialog"] button')).find((b) => b.textContent === copy("dataDlgConfirm"))!
      act(() => confirm.click())
      expect(onClear).toHaveBeenCalledOnce()
      act(() => root.unmount())
      host.remove()
    })
  }
})
