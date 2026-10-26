/** Question box. Sends the text and can stop a running answer. */

import { useEffect, useId, useState, useRef, type ClipboardEvent, type FormEvent, type KeyboardEvent } from "react"
import type { CopyKey } from "../../i18n"

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
  preview: string | null
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
          aria-describedby={cut || showCount ? noteId : undefined}
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
            disabled={!ready}
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
      <div className={`mt-2 w-full ${placement === "dock" ? "mx-auto max-w-5xl" : ""}`}>
        {showNote ? (
          <p className="text-sm text-muted">
            {copy("disclaimerShort")}
            {showHint ? ` · ${copy("enterHint")}` : null}
          </p>
        ) : null}
        {showCount ? (
          <p id={cut ? undefined : noteId} className={`text-sm ${countWarn ? "text-warning" : "text-muted"}`}>
            {copy("charCount").replace("{count}", count.toLocaleString("en-US"))}
          </p>
        ) : null}
        {cut ? (
          <p id={noteId} className="mt-1 text-sm text-warning" role="alert">
            {copy("pasteCut")}
          </p>
        ) : null}
        {preview ? (
          <p className="mt-1 max-w-[68ch] text-sm">
            {copy("redactionPreview")} {preview}
          </p>
        ) : null}
        {error ? (
          <p className="mt-1 text-sm text-low" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </form>
  )
}
