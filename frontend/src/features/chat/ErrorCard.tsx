/** Failed answer: the real reason, a code chip, and retry. */

import type { CopyKey } from "../../i18n"
import { chipLabel, type TurnError } from "./failure"

type Copy = (key: CopyKey) => string

export default function ErrorCard({
  error,
  secondsLeft,
  copy,
  onRetry,
  onCopy,
  onCancel,
}: {
  error: TurnError
  secondsLeft: number | null
  copy: Copy
  onRetry: () => void
  onCopy: () => void
  onCancel: () => void
}) {
  return (
    <div
      data-motion-slot="error-card"
      role="alert"
      className="border border-rule bg-field px-4 py-4"
      style={{ borderInlineStartWidth: 4, borderInlineStartColor: "var(--low)" }}
    >
      <h3 className="font-statute text-lg font-medium">{copy("answerFailedTitle")}</h3>
      <p className="mt-3 inline-block bg-elevated px-2 py-1 text-xs font-medium text-low">{chipLabel(error)}</p>
      <p className="mt-3 max-w-[68ch] text-sm">{error.message}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={onRetry} className="min-h-11 bg-seal px-4 text-sm font-medium text-seal-ink">
          {copy("retry")}
        </button>
        <button type="button" onClick={onCopy} className="min-h-11 border border-rule px-3 text-sm">
          {copy("copyQuestion")}
        </button>
      </div>
      {secondsLeft != null ? (
        <p className="mt-3 text-sm text-muted">
          {copy("autoRetrySaved")} {secondsLeft} s.{" "}
          <button type="button" onClick={onCancel} className="text-seal">
            {copy("cancelAutoRetry")}
          </button>
        </p>
      ) : null}
    </div>
  )
}
