// @vitest-environment happy-dom
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { t } from "../i18n"
import AppFooter from "./AppFooter"

describe("AppFooter", () => {
  it("renders EN disclaimer and credit", () => {
    const html = renderToStaticMarkup(<AppFooter copy={(k) => t("en", k)} />)
    expect(html).toContain("not affiliated with the Government of Pakistan")
    expect(html).toContain("Made by Kasaam Ali")
  })
  it("renders Roman Urdu copy", () => {
    const html = renderToStaticMarkup(<AppFooter copy={(k) => t("roman_urdu", k)} />)
    expect(html).toContain("azaad project")
    expect(html).toContain("Kasaam Ali ne banaya")
  })
})
