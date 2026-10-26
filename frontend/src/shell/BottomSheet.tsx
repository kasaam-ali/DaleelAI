/** Phone bottom sheet (SPEC §10.1): grab handle, scrim, sticky title row with Close; a modal dialog via useModal. */

import { useId, useRef, type ReactNode } from "react"
import Icon from "./icons"
import { useModal } from "./useModal"

export default function BottomSheet({
  title,
  closeLabel,
  className = "",
  onClose,
  children,
}: {
  title: string
  closeLabel: string
  className?: string
  onClose: () => void
  children: ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  const titleId = useId()
  useModal(true, ref, onClose)
  return (
    <>
      <div className="m-scrim" data-modal-scrim aria-hidden="true" onClick={onClose} />
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId} className={`m-sheet ${className}`}>
        <span className="grab" aria-hidden="true" />
        <div className="ms-head">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="iconbtn" data-sheet-close aria-label={closeLabel} title={closeLabel} onClick={onClose}>
            <Icon name="close" size="sm" />
          </button>
        </div>
        <div className="ms-body">{children}</div>
      </div>
    </>
  )
}
