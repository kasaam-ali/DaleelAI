/** Question box. Sends the text and can stop a running answer. */

import { useEffect, useId, useState, useRef, type ClipboardEvent, type FormEvent, type KeyboardEvent } from "react"
import type { CopyKey } from "../../i18n"
import type { RedactedPart } from "../../lib/pii"
import Icon from "../../shell/icons"
import "./guard.css"

type Copy = (key: CopyKey) => string

const QUESTION_LIMIT = 2000
const COUNTER_FROM = 1500
const WARN_FROM = 1800

export default function Composer({
  value,
  busy,
  error,
  preview,
  copy,
  onChange,
  onSubmit,
  onStop,
  placement = "dock",
  fieldId = "question",
  muted = false,
  placeholder,
  size = "default",
  showHint = true,
  showNote = true,
}: {
  value: string
  busy: boolean
  error: string | null
  /** The masked question, split so placeholders can be highlighted. Null when nothing is masked. */
  preview: RedactedPart[] | null
  copy: Copy
  onChange: (value: string) => void
  onSubmit: () => void
  onStop: () => void
  placement?: "dock" | "field"
  fieldId?: string
  muted?: boolean
  placeholder?: string
  size?: "default" | "large"
  showHint?: boolean
  /** Home shows the disclaimer once at the page foot instead (premium-home.html). */
  showNote?: boolean
}) {
  const field = useRef<HTMLTextAreaElement>(null)
  const noteId = useId()
  const [pasteCut, setPasteCut] = useState(false)
  const count = value.length
  const showCount = count >= COUNTER_FROM
  const countWarn = count >= WARN_FROM
  const cut = pasteCut && count >= QUESTION_LIMIT

  useEffect(() => {
    const element = field.current
    if (!element) return
    element.style.height = "auto"
    element.style.height = `${Math.min(element.scrollHeight, 160)}px`
  }, [value])

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      if (!busy) onSubmit()
    }
  }

  function onForm(event: FormEvent) {
    event.preventDefault()
    if (busy) onStop()
    else onSubmit()
  }

  function onPaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const pasted = event.clipboardData?.getData("text") ?? ""
    if (!pasted) return
    event.preventDefault()
    const el = event.currentTarget
    const start = el.selectionStart ?? value.length
    const end = el.selectionEnd ?? value.length
    const next = value.slice(0, start) + pasted + value.slice(end)
    const cut = next.length > QUESTION_LIMIT
    onChange(cut ? next.slice(0, QUESTION_LIMIT) : next)
    setPasteCut(cut)
  }

  const ready = value.trim().length > 0
  const hint = error === copy("writeQuestion") || (value.length > 0 && !ready) ? copy("writeQuestion") : null
  const failure = error && error !== copy("writeQuestion") ? error : null
  const previewId = `${noteId}-preview`
  const describedBy = [cut || showCount || hint || failure ? noteId : "", preview ? previewId : ""].filter(Boolean).join(" ")

  return (
    <form
      onSubmit={onForm}
      data-composer={placement}
      className={placement === "dock" ? "border-t border-rule bg-paper px-4 py-3" : ""}
    >
      <div
        className={`composer flex w-full items-end gap-2 border border-rule bg-field px-2 py-2 ${
          placement === "dock" ? "mx-auto max-w-5xl" : ""
        } ${size === "large" ? "rounded-2xl px-3 shadow-[var(--shadow)]" : ""}`}
      >
        <label htmlFor={fieldId} className="sr-only">
          {copy("questionLabel")}
        </label>
        <textarea
          id={fieldId}
          ref={field}
          rows={1}
          value={value}
          maxLength={QUESTION_LIMIT}
          onChange={(event) => {
            onChange(event.target.value)
            if (event.target.value.length < QUESTION_LIMIT) setPasteCut(false)
          }}
          onPaste={onPaste}
          onKeyDown={onKeyDown}
          placeholder={placeholder ?? copy("placeholder")}
          aria-describedby={describedBy || undefined}
          className={`max-h-40 w-full resize-none bg-transparent px-2 py-3 text-base text-ink outline-none ${
            size === "large" ? "min-h-14" : "min-h-12"
          }`}
        />
        {busy ? (
          <button
            type="submit"
            aria-label={copy("stop")}
            className="mb-1 inline-flex h-11 min-w-11 items-center justify-center border border-low px-3 text-sm font-medium text-low"
          >
            {copy("stop")}
          </button>
        ) : (
          <button
            type="submit"
            aria-disabled={!ready}
            data-ready={ready ? "true" : "false"}
            aria-label={copy("send")}
            className={`mb-1 inline-flex h-11 min-w-11 shrink-0 items-center justify-center px-4 text-sm font-medium ${
              ready ? "bg-seal text-seal-ink" : "cursor-not-allowed border border-rule bg-elevated text-placeholder"
            } ${
              size === "large" ? "rounded-lg" : ""
            } ${muted ? "opacity-60" : ""}`}
          >
            {copy("send")}
            {size === "large" ? (
              <svg viewBox="0 0 24 24" aria-hidden="true" className="ml-1.5 h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <path d="m9 6 6 6-6 6" />
              </svg>
            ) : null}
          </button>
        )}
      </div>
      <div className={`gmeta mt-2 w-full ${placement === "dock" ? "mx-auto max-w-5xl" : ""}`}>
        {preview ? (
          <p className="gprev" id={previewId} aria-live="polite">
            <span className="h">
              <Icon name="lock" size="sm" />
              {copy("redactionPreview")}
            </span>
            <span className="pv">
              {copy("redactionWillSend")} <b><Masked parts={preview} /></b>
            </span>
          </p>
        ) : null}
        <span id={noteId} className="contents">
          {cut ? (
            <p className="gerr" role="status">
              <Icon name="alert" size="sm" />
              <span>
                {copy("pasteCutTitle")}
                <small>{copy("pasteCutDetail")}</small>
              </span>
            </p>
          ) : null}
          {hint && !cut ? (
            <p className="gerr mut" role="status">
              <Icon name="info" size="sm" />
              <span>{hint}</span>
            </p>
          ) : null}
          {failure ? (
            <p className="gerr e" role="alert">
              <Icon name="alert" size="sm" />
              <span>{failure}</span>
            </p>
          ) : null}
          {showCount ? (
            <p className={`gcnt${countWarn ? " warn" : ""}`}>
              {copy("charCounter").replace("{count}", count.toLocaleString("en-US"))}
            </p>
          ) : null}
        </span>
      </div>
      {showNote ? (
        <p className={`composer-note mt-2 w-full text-sm text-muted ${placement === "dock" ? "mx-auto max-w-5xl" : ""}`}>
          {copy("disclaimerShort")}
          {showHint ? ` · ${copy("enterHint")}` : null}
        </p>
      ) : null}
    </form>
  )
}

/** Masked text with each placeholder ([CNIC], [NTN], …) highlighted. */
export function Masked({ parts }: { parts: RedactedPart[] }) {
  return (
    <>
      {parts.map((part, index) =>
        part.tag ? (
          <mark key={index} className="mk">
            {part.text}
          </mark>
        ) : (
          <span key={index}>{part.text}</span>
        ),
      )}
    </>
  )
}
