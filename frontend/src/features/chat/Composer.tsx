/** Question box. Sends the text and can stop a running answer. */

import { useEffect, useRef, type FormEvent, type KeyboardEvent } from "react"
import type { CopyKey } from "../../i18n"

type Copy = (key: CopyKey) => string

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
}) {
  const field = useRef<HTMLTextAreaElement>(null)

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

  const ready = value.trim().length > 0

  return (
    <form
      onSubmit={onForm}
      className={placement === "dock" ? "border-t border-rule bg-paper px-4 py-3" : ""}
    >
      <div
        className={`composer flex w-full items-end gap-2 border border-rule bg-field px-2 py-2 ${
          placement === "dock" ? "mx-auto max-w-5xl" : ""
        }`}
      >
        <label htmlFor={fieldId} className="sr-only">
          {copy("questionLabel")}
        </label>
        <textarea
          id={fieldId}
          ref={field}
          rows={1}
          value={value}
          maxLength={2000}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={copy("placeholder")}
          className="max-h-40 min-h-12 w-full resize-none bg-transparent px-2 py-3 text-base text-ink outline-none"
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
            aria-label={copy("send")}
            className="mb-1 inline-flex h-11 min-w-11 items-center justify-center bg-seal px-4 text-sm font-medium text-seal-ink disabled:cursor-not-allowed disabled:opacity-40"
          >
            {copy("send")}
          </button>
        )}
      </div>
      <div className={`mt-2 w-full ${placement === "dock" ? "mx-auto max-w-5xl" : ""}`}>
        <p className="text-sm text-muted">{copy("enterHint")}</p>
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
