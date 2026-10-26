/** Confirm or cancel. Cancel is focused first, and Tab stays inside the dialog. */

import { useRef, type ReactNode } from "react"
import { useModal } from "./useModal"

export default function ConfirmDialog({
  title,
  body,
  confirmLabel,
  cancelLabel,
  pending = false,
  onConfirm,
  onCancel,
}: {
  title: string
  body: ReactNode
  confirmLabel: string
  cancelLabel: string
  pending?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  const panelRef = useRef<HTMLDivElement>(null)
  useModal(true, panelRef, () => {
    if (!pending) onCancel()
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="motion-scrim absolute inset-0 bg-ink/45" onClick={() => { if (!pending) onCancel() }} />
      <div
        ref={panelRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-body"
        data-motion="rise"
        className="motion-rise relative w-full max-w-[22rem] rounded-2xl border border-rule bg-field p-5 shadow-[0_12px_40px_rgba(23,33,29,0.16)]"
      >
        <span
          className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[color-mix(in_srgb,var(--low)_12%,var(--field))] text-low"
          aria-hidden="true"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path d="M5 7.5h14M9.5 7.5V5.8h5V7.5M7.2 7.5l.7 11h8.2l.7-11" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <h2 id="confirm-dialog-title" className="mt-3 text-base font-medium text-ink">
          {title}
        </h2>
        <p id="confirm-dialog-body" className="mt-2 text-sm leading-relaxed text-muted">
          {body}
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={pending}
            className="min-h-11 rounded-lg border border-rule bg-field px-3 text-sm"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={pending}
            data-destructive
            className="min-h-11 rounded-lg bg-error px-3 text-sm font-medium text-on-strong"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
