/** New chat shows the filing context and four suggestions. */

// @vitest-environment happy-dom
import { createRoot, type Root } from "react-dom/client"
import { act } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import NewChat from "./NewChat"

const copy = (key: string) =>
  (
    {
      askDaleel: "Ask DaleelAI",
      newChatTitle: "Ask about Pakistan's federal tax law.",
      newChatPlaceholder: "Ask a tax question in English or Roman Urdu...",
      answersUse: "Answers use",
      editFiling: "Edit",
      suggestFreelance: "Freelance & IT export",
      suggestProperty: "Property · capital gains",
      suggestFiler: "Filer status",
      suggestLate: "Deadlines & penalties",
      trustCited: "Cites the exact section",
      trustRoman: "Roman Urdu understood",
      trustHonest: "Says when it doesn't know",
      freelancer: "Freelancer",
      filer: "Filer",
      punjab: "Punjab",
      questionLabel: "Your question",
      send: "Send",
      stop: "Stop",
      taxYearLabel: "Tax year",
      profileTitle: "Filing details",
      profileHelp: "Saved on this device.",
      taxpayerType: "Taxpayer type",
      filerStatus: "Filer status",
      province: "Province",
      choose: "Choose",
      salaried: "Salaried",
      business: "Small business",
      company: "Company",
      nonFiler: "Non-filer",
      notSure: "Not sure",
      sindh: "Sindh",
      kpk: "Khyber Pakhtunkhwa",
      balochistan: "Balochistan",
      islamabad: "Islamabad",
      gb: "Gilgit-Baltistan",
      ajk: "Azad Kashmir",
    } as Record<string, string>
  )[key] ?? key

describe("NewChat", () => {
  let root: Root
  let host: HTMLDivElement

  afterEach(() => {
    act(() => root?.unmount())
    host?.remove()
  })

  it("lists four suggestions and the filing context that will be sent", async () => {
    const onPick = vi.fn()
    host = document.createElement("div")
    document.body.append(host)
    root = createRoot(host)
    await act(async () => {
      root.render(
        <NewChat
          copy={copy as never}
          profile={{ taxpayer_type: "freelancer", filer_status: "filer", province: "punjab" }}
          taxYear="TY2026"
          draft=""
          busy={false}
          error={null}
          preview={null}
          onDraft={() => undefined}
          onSubmit={() => undefined}
          onStop={() => undefined}
          onProfile={() => undefined}
          onTaxYear={() => undefined}
          onPick={onPick}
        />,
      )
    })
    expect(host.textContent).toContain("Ask about Pakistan's federal tax law.")
    expect(host.textContent).toContain("Freelancer · Filer · Punjab · TY2026")
    expect(host.textContent).toContain("Freelancer ki income par kitna tax lagta hai?")
    expect(host.textContent).toContain("Do I pay tax on a property sale after 4 years?")
    expect(host.textContent).toContain("Filer aur non-filer mein kya farq hai?")
    expect(host.textContent).toContain("What happens if I file my return late?")
    const suggestion = [...host.querySelectorAll("button")].find((button) =>
      button.textContent?.includes("Freelancer ki income"),
    )
    await act(async () => {
      suggestion?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    })
    expect(onPick).toHaveBeenCalledWith("Freelancer ki income par kitna tax lagta hai?")
  })
})
