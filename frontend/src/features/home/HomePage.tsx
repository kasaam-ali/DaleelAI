import { useState } from "react"
import type { CopyKey } from "../../i18n"
import { redactPii } from "../../lib/pii"
import Composer from "../chat/Composer"
import Icon, { type IconName } from "../../shell/icons"
import type { AppView } from "../../shell/AppShell"

type Copy = (key: CopyKey) => string

const TOOLS: { id: AppView; label: CopyKey; hint: CopyKey; icon: IconName }[] = [
  { id: "chat", label: "homeToolAsk", hint: "hintAsk", icon: "chat" },
  { id: "calculator", label: "homeToolCalc", hint: "hintCalc", icon: "calculator" },
  { id: "filer", label: "homeToolFiler", hint: "hintFiler", icon: "filer" },
  { id: "notice", label: "homeToolNotice", hint: "hintNotice", icon: "notice" },
  { id: "checklist", label: "homeToolChecklist", hint: "hintChecklist", icon: "checklist" },
  { id: "experts", label: "homeToolExperts", hint: "hintExperts", icon: "experts" },
  { id: "updates", label: "homeToolUpdates", hint: "hintUpdates", icon: "updates" },
  { id: "evaluation", label: "homeToolEval", hint: "hintEval", icon: "evaluation" },
]

const QUESTIONS = [
  "starterSalary",
  "starterNotice",
  "starterAtl",
  "starterFreelance",
  "starterReturn",
  "starterWithholding",
] as const

export default function HomePage({
  copy,
  onOpen,
  onAsk,
}: {
  copy: Copy
  onOpen: (view: AppView) => void
  onAsk: (question: string) => void
}) {
  const [draft, setDraft] = useState("")
  const [error, setError] = useState<string | null>(null)
  const preview = redactPii(draft)
  const showPreview = draft.trim().length > 0 && preview !== draft

  function submit() {
    const question = draft.trim()
    if (!question) {
      setError(copy("writeQuestion"))
      return
    }
    setError(null)
    setDraft("")
    onAsk(question)
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-8">
        <h2 className="max-w-[18ch] font-statute text-[2.35rem] leading-[1.08] font-medium tracking-tight text-ink">
          {copy("homeTitle")}
        </h2>
        <div className="mt-6">
          <Composer
            value={draft}
            busy={false}
            error={error}
            preview={showPreview ? preview : null}
            copy={copy}
            placement="field"
            fieldId="home-question"
            onChange={(value) => {
              setDraft(value)
              setError(null)
            }}
            onSubmit={submit}
            onStop={() => undefined}
          />
        </div>
        <p className="mt-4 max-w-[58ch] text-base leading-relaxed text-muted">{copy("homePurpose")}</p>
        <ul className="mt-8 grid border-t border-rule sm:grid-cols-2">
          {TOOLS.map((tool) => (
            <li key={tool.id} className="border-b border-rule sm:odd:border-r sm:odd:pr-0">
              <button
                type="button"
                onClick={() => onOpen(tool.id)}
                className="flex min-h-16 w-full items-start gap-3 px-1 py-3 text-left hover:bg-mint/50 sm:px-4"
              >
                <span className="mt-0.5 text-seal">
                  <Icon name={tool.icon} />
                </span>
                <span>
                  <span className="block text-sm font-medium text-ink">{copy(tool.label)}</span>
                  <span className="mt-0.5 block text-sm leading-snug text-muted">{copy(tool.hint)}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
        <h3 className="mt-10 text-base font-medium text-ink">{copy("homeQuestions")}</h3>
        <ul className="mt-2 border-t border-rule">
          {QUESTIONS.map((key) => (
            <li key={key} className="border-b border-rule">
              <button
                type="button"
                onClick={() => onAsk(copy(key))}
                className="min-h-12 w-full py-2 text-left text-sm leading-snug hover:text-seal"
              >
                {copy(key)}
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-8 max-w-[62ch] text-sm leading-relaxed text-muted">{copy("homeTrust")}</p>
      </div>
    </div>
  )
}
