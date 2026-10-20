/** The prompt-injection refusal gets its own header, not the "hiding income" one. */

// @vitest-environment happy-dom
Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })

import { act } from "react"
import { createRoot } from "react-dom/client"
import { describe, expect, it } from "vitest"
import { t, type CopyKey } from "../../i18n"
import RefusalCard from "./RefusalCard"

function render(reason: string, language: "en" | "roman_urdu") {
  const host = document.createElement("div")
  document.body.append(host)
  const root = createRoot(host)
  act(() => {
    root.render(
      <RefusalCard
        kind="declined"
        reason={reason}
        authority={null}
        query={null}
        retrieved={null}
        suggestions={[]}
        links={[]}
        copy={(key: CopyKey) => t(language, key)}
        onAsk={() => undefined}
      />,
    )
  })
  const text = host.textContent ?? ""
  act(() => root.unmount())
  host.remove()
  return text
}

describe("RefusalCard injection header", () => {
  it("uses the injection header in both shells", () => {
    const en = render(t("en", "injectionRefusal"), "en")
    expect(en).toContain("I can't change my rules")
    expect(en).not.toContain("hiding income")
    const ru = render(t("roman_urdu", "injectionRefusal"), "roman_urdu")
    expect(ru).toContain("Main apne qawaid nahi badal sakta")
    expect(ru).not.toContain("Income chhupane mein madad")
  })

  it("keeps the evasion header for evasion", () => {
    expect(render(t("en", "evasionRefusal"), "en")).toContain("I can't help with hiding income")
  })
})
