/** Empty chat: headline, composer, filing context, and four suggestions. */

import { useEffect, useId, useRef, useState } from "react"
import type { CopyKey } from "../../i18n"
import type { ClientTaxYear, Profile } from "../../lib/session"
import Icon, { type IconName } from "../../shell/icons"
import ProfilePanel from "../onboarding/ProfilePanel"
import Composer from "./Composer"
import { filingSummary } from "./filingSummary"

type Copy = (key: CopyKey) => string


const SUGGESTIONS: { question: string; hint: CopyKey; icon: IconName }[] = [
  {
    question: "Freelancer ki income par kitna tax lagta hai?",
    hint: "suggestFreelance",
    icon: "chat",
  },
  {
    question: "Do I pay tax on a property sale after 4 years?",
    hint: "suggestProperty",
    icon: "notice",
  },
  {
    question: "Filer aur non-filer mein kya farq hai?",
    hint: "suggestFiler",
    icon: "privacy",
  },
  {
    question: "What happens if I file my return late?",
    hint: "suggestLate",
    icon: "updates",
  },
]


export default function NewChat({
  copy,
  profile,
  taxYear,
  draft,
  busy,
  error,
  preview,
  onDraft,
  onSubmit,
  onStop,
  onProfile,
  onTaxYear,
  onPick,
}: {
  copy: Copy
  profile: Profile
  taxYear: ClientTaxYear
  draft: string
  busy: boolean
  error: string | null
  preview: string | null
  onDraft: (value: string) => void
  onSubmit: () => void
  onStop: () => void
  onProfile: (patch: Partial<Profile>) => void
  onTaxYear: (taxYear: ClientTaxYear) => void
  onPick: (question: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const editRef = useRef<HTMLDivElement>(null)
  const editId = useId()
  const summary = filingSummary(profile, taxYear, copy)

  useEffect(() => {
    if (!editing) return
    function onPointer(event: MouseEvent) {
      if (!editRef.current?.contains(event.target as Node)) setEditing(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setEditing(false)
    }
    document.addEventListener("mousedown", onPointer)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onPointer)
      document.removeEventListener("keydown", onKey)
    }
  }, [editing])

  return (
    <div className="mx-auto w-full max-w-[760px] py-4" data-motion="rise">
      <p className="inline-flex items-center gap-1.5 text-[13px] font-medium tracking-[0.06em] text-seal uppercase">
        <span aria-hidden="true">✦</span>
        {copy("askDaleel")}
      </p>
      <h1 className="mt-3 max-w-[18ch] font-statute text-[clamp(2rem,3vw,2.75rem)] leading-[1.06] font-medium tracking-[-0.034em] text-ink">
        {copy("newChatTitle")}
      </h1>
      <div className="mt-6" data-motion="rise">
        <Composer
          value={draft}
          busy={busy}
          error={error}
          preview={preview}
          copy={copy}
          placement="field"
          fieldId="new-chat-question"
          placeholder={copy("newChatPlaceholder")}
          size="large"
          showHint={false}
          onChange={onDraft}
          onSubmit={onSubmit}
          onStop={onStop}
        />
      </div>
      <div ref={editRef} className="relative mt-3 flex flex-wrap items-center gap-2 text-sm text-muted">
        <span>{copy("answersUse")}</span>
        <span className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-rule bg-field px-2.5 py-1 text-ink">
          <Icon name="search" />
          <span className="truncate">{summary}</span>
        </span>
        <button
          type="button"
          aria-expanded={editing}
          aria-controls={editId}
          onClick={() => setEditing((open) => !open)}
          className="font-medium text-seal"
        >
          {copy("editFiling")}
        </button>
        {editing ? (
          <div
            id={editId}
            data-motion="rise"
            className="motion-rise absolute top-full left-0 z-20 mt-2 w-[min(24rem,calc(100vw-3rem))] rounded-2xl border border-rule bg-field p-3 shadow-[0_12px_40px_rgba(23,33,29,0.16)]"
          >
            <ProfilePanel profile={profile} copy={copy} onChange={onProfile} compact idPrefix="context-" />
            <p className="mt-3 text-sm">{copy("taxYearLabel")}</p>
            <div className="mt-1 flex rounded-lg bg-elevated p-1">
              {(["TY2026", "TY2027"] as const).map((year) => (
                <button
                  key={year}
                  type="button"
                  aria-pressed={taxYear === year}
                  onClick={() => onTaxYear(year)}
                  className={`min-h-10 flex-1 rounded-md text-sm ${taxYear === year ? "bg-field font-medium text-seal" : ""}`}
                >
                  {year}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>
      <ul className="stagger mt-5 grid gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map((item) => (
          <li key={item.question}>
            <button
              type="button"
              onClick={() => onPick(item.question)}
              className="flex h-full w-full items-start gap-3 rounded-2xl border border-rule bg-field p-4 text-left shadow-[var(--shadow)] hover:border-seal"
            >
              <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-mint text-seal">
                <Icon name={item.icon} />
              </span>
              <span>
                <span className="block text-sm font-medium leading-snug text-ink">{item.question}</span>
                <span className="mt-1 block text-xs text-muted">{copy(item.hint)}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
        <li className="inline-flex items-center gap-1.5">
          <Icon name="privacy" />
          {copy("trustCited")}
        </li>
        <li className="inline-flex items-center gap-1.5">
          <span aria-hidden="true">◇</span>
          {copy("trustRoman")}
        </li>
        <li className="inline-flex items-center gap-1.5">
          <span aria-hidden="true">○</span>
          {copy("trustHonest")}
        </li>
      </ul>
    </div>
  )
}
