/** Filing step: empty, partial and saved states; Save waits for taxpayer type + filer status. */

// @vitest-environment happy-dom
import { act } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { t, type CopyKey } from "../../i18n"
import { filingCount, type Profile } from "../../lib/session"
import FilingStep from "./FilingStep"

const copy = (key: CopyKey) => t("en", key)
let root: Root
let host: HTMLDivElement

function render(profile: Profile, extra: { saved?: boolean; taxYearSet?: boolean } = {}) {
  const props = {
    profile,
    taxYear: "TY2026" as const,
    taxYearSet: extra.taxYearSet ?? false,
    saved: extra.saved ?? false,
    copy,
    onChange: vi.fn(),
    onTaxYear: vi.fn(),
    onSave: vi.fn(),
    onEdit: vi.fn(),
  }
  act(() => root.render(<FilingStep {...props} />))
  return props
}

const save = () => Array.from(host.querySelectorAll("button")).find((button) => button.textContent?.includes("Save details"))!

beforeEach(() => {
  host = document.createElement("div")
  document.body.append(host)
  root = createRoot(host)
})
afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

describe("FilingStep", () => {
  it("starts empty with 0 of 4 and a disabled Save", () => {
    const props = render({ taxpayer_type: null, filer_status: null, province: null })
    expect(host.querySelector("section")?.getAttribute("data-state")).toBe("empty")
    expect(host.textContent).toContain("0 of 4")
    expect(save().getAttribute("aria-disabled")).toBe("true")
    act(() => save().click())
    expect(props.onSave).not.toHaveBeenCalled()
  })

  it("keeps Save disabled with only one of the two required fields", () => {
    render({ taxpayer_type: null, filer_status: "filer", province: "punjab" }, { taxYearSet: true })
    expect(host.textContent).toContain("3 of 4")
    expect(save().getAttribute("aria-disabled")).toBe("true")
  })

  it("fills the meter to 2 of 4 and enables Save once taxpayer type and filer status are set", () => {
    const props = render({ taxpayer_type: "freelancer", filer_status: "filer", province: null })
    expect(host.querySelector("section")?.getAttribute("data-state")).toBe("partial")
    expect(host.textContent).toContain("2 of 4")
    expect(host.querySelectorAll(".prog i.on")).toHaveLength(2)
    expect(save().getAttribute("aria-disabled")).toBe("false")
    act(() => save().click())
    expect(props.onSave).toHaveBeenCalledOnce()
  })

  it("writes the filer segment, the selects and the tax year", () => {
    const props = render({ taxpayer_type: null, filer_status: null, province: null })
    const radio = (name: string) => Array.from(host.querySelectorAll('[role="radio"]')).find((item) => item.textContent === name) as HTMLButtonElement
    act(() => radio("Non-filer").click())
    expect(props.onChange).toHaveBeenCalledWith({ filer_status: "non_filer" })
    act(() => radio("TY2027").click())
    expect(props.onTaxYear).toHaveBeenCalledWith("TY2027")
    const select = host.querySelector<HTMLSelectElement>("#fs-taxpayer")!
    act(() => {
      select.value = "salaried"
      select.dispatchEvent(new Event("change", { bubbles: true }))
    })
    expect(props.onChange).toHaveBeenCalledWith({ taxpayer_type: "salaried" })
    // The tax year default is not shown as picked until the user picks it.
    expect(radio("TY2026").getAttribute("aria-checked")).toBe("false")
  })

  it("collapses to the saved summary with four pills and Edit", () => {
    const props = render({ taxpayer_type: "freelancer", filer_status: "filer", province: "punjab" }, { saved: true, taxYearSet: true })
    expect(host.querySelector("section")?.getAttribute("data-state")).toBe("saved")
    expect(Array.from(host.querySelectorAll(".pill")).map((pill) => pill.textContent)).toEqual([
      "Filer statusFiler",
      "Taxpayer typeFreelancer",
      "ProvincePunjab",
      "Tax yearTY2026",
    ])
    expect(host.textContent).toContain("Sent with every question")
    const edit = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "Edit")!
    act(() => edit.click())
    expect(props.onEdit).toHaveBeenCalledOnce()
  })

  it("counts the four fields", () => {
    expect(filingCount({ taxpayer_type: null, filer_status: null, province: null }, false)).toBe(0)
    expect(filingCount({ taxpayer_type: "company", filer_status: "unknown", province: "sindh" }, true)).toBe(4)
  })
})
