/** EN | Roman Urdu control for the answer, separate from the shell language. */

import type { CopyKey } from "../../i18n"
import type { ReplyLanguage } from "../../lib/session"

type Copy = (key: CopyKey) => string

const OPTIONS: { id: ReplyLanguage; label: string }[] = [
  { id: "en", label: "EN" },
  { id: "roman_urdu", label: "Roman Urdu" },
]

export default function AnswerHeader({
  detected,
  selected,
  copy,
  onSelect,
}: {
  detected: ReplyLanguage | null
  selected: ReplyLanguage | null
  copy: Copy
  onSelect: (language: ReplyLanguage) => void
}) {
  if (!detected) return null
  return (
    <div
      data-motion-slot="answer-header"
      className="mb-3 flex flex-wrap items-center gap-2 text-sm text-muted"
    >
      <span>{detected === "roman_urdu" ? copy("detectedRomanUrdu") : copy("detectedEnglish")}</span>
      <span aria-hidden="true">·</span>
      <span>{copy("answerIn")}</span>
      <div role="radiogroup" aria-label={copy("answerIn")} className="inline-flex gap-1 bg-elevated p-1">
        {OPTIONS.map((option) => (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={selected === option.id}
            onClick={() => onSelect(option.id)}
            className={`min-h-11 px-3 text-sm ${selected === option.id ? "bg-field font-medium text-ink" : ""}`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}
