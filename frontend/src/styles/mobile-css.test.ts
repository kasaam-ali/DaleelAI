/** PR M1: phone CSS sits inside the ≤767 query (desktop unchanged). */

import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

describe("phone CSS stays inside the ≤767 query", () => {
  const shellCss = readFileSync(new URL("../shell/shell.css", import.meta.url), "utf8")
  const homeCss = readFileSync(new URL("../features/home/home.css", import.meta.url), "utf8")
  it("hides the theme toggle and shows the banner only on phones", () => {
    const phone = shellCss.slice(shellCss.indexOf("@media (max-width: 767px) {"))
    expect(phone).toContain(".dtop .theme-toggle { display: none; }")
    expect(phone).toContain(".m-disc { display: flex;")
    expect(shellCss.slice(0, shellCss.indexOf("@media (max-width: 767px) {"))).toContain(".m-disc { display: none; }")
  })
  it("home: chip, sheet one column with no-wrap segments, sideways tool cards at 82%", () => {
    const phone = homeCss.slice(homeCss.indexOf("/* ---- Phones ≤767"))
    expect(phone.startsWith("/* ---- Phones ≤767")).toBe(true)
    expect(phone).toContain(".phome .fstep.in-sheet .fs-grid { display: grid; grid-template-columns: 1fr !important;")
    expect(phone).toContain(".phome .fstep.in-sheet .sg button { flex: 1; min-height: 44px; white-space: nowrap; }")
    expect(phone).toContain(".phome .tools3 .tcard { flex: 0 0 82%;")
    for (const rule of [".fchip", ".in-sheet", "flex: 0 0 82%"]) expect(homeCss.slice(0, homeCss.indexOf("/* ---- Phones ≤767"))).not.toContain(rule)
  })
})
