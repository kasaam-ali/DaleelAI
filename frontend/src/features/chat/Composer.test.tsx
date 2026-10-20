/** A paste past 2,000 characters warns instead of disappearing quietly. */

// @vitest-environment happy-dom
import { useState } from "react"
import { createRoot, type Root } from "react-dom/client"
import { act } from "react"
import { afterEach, describe, expect, it } from "vitest"
import { t, type CopyKey } from "../../i18n"
import type { UiLanguage } from "../../lib/session"
import Composer from "./Composer"

function copyFor(language: UiLanguage) {
  return (key: CopyKey) => t(language, key)
}

function Harness({ language, initial = "" }: { language: UiLanguage; initial?: string }) {
  const [value, setValue] = useState(initial)
  return (
    <Composer
      value={value}
      busy={false}
      error={null}
      preview={null}
      copy={copyFor(language)}
      onChange={setValue}
      onSubmit={() => undefined}
      onStop={() => undefined}
    />
  )
}

describe("Composer paste limit", () => {
  let root: Root | undefined
  let host: HTMLDivElement | undefined

  afterEach(() => {
    act(() => root?.unmount())
    host?.remove()
  })

  async function render(language: UiLanguage, initial = "") {
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root?.render(<Harness language={language} initial={initial} />)
    })
    const field = host.querySelector("textarea")
    if (!field) throw new Error("missing question box")
    return field
  }

  function paste(field: HTMLTextAreaElement, text: string) {
    const transfer = new DataTransfer()
    transfer.setData("text", text)
    const event = new ClipboardEvent("paste", { bubbles: true, cancelable: true, clipboardData: transfer })
    act(() => {
      field.dispatchEvent(event)
    })
  }

  it("shows the English cut warning and keeps the first 2,000 characters", async () => {
    const field = await render("en")
    paste(field, "a".repeat(2500))
    expect(field.value).toHaveLength(2000)
    expect(field.value.endsWith("a")).toBe(true)
    expect(host?.textContent).toContain(
      "Your paste was cut at 2,000 characters.Check the end of your question before sending.",
    )
    expect(host?.textContent).toContain("2,000 / 2,000")
    expect(host?.querySelector(".gcnt.warn")).toBeTruthy()
  })

  it("shows the Roman Urdu cut warning", async () => {
    const field = await render("roman_urdu")
    paste(field, "ب".repeat(2001))
    expect(field.value).toHaveLength(2000)
    expect(host?.textContent).toContain(
      "Aap ka paste 2,000 harf par kat gaya.Bhejne se pehle sawal ka aakhri hissa check karein.",
    )
    expect(host?.textContent).toContain("2,000 / 2,000")
  })

  it("leaves a shorter paste alone and counts from 1,500", async () => {
    const field = await render("en", "b".repeat(1499))
    expect(host?.textContent).not.toContain("/ 2,000")
    paste(field, "c")
    expect(field.value).toHaveLength(1500)
    expect(host?.textContent).toContain("1,500 / 2,000")
    expect(host?.textContent).not.toContain("Your paste was cut")
    expect(host?.querySelector(".gcnt.warn")).toBeNull()
  })

  it("warns the counter from 1,800 characters", async () => {
    await render("en", "d".repeat(1800))
    expect(host?.textContent).toContain("1,800 / 2,000")
    expect(host?.querySelector(".gcnt.warn")).toBeTruthy()
    expect(host?.textContent).not.toContain("Your paste was cut")
  })
})
