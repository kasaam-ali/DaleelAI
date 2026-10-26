/** Service status at the foot of both sidebars; opens About & settings (handoff-pr18-nav.md §3). */

import type { CopyKey } from "../i18n"

import { statusText, type Service } from "./navEvents"

type Copy = (key: CopyKey) => string

export default function StatusRow({ service, copy, onOpen }: { service: Service; copy: Copy; onOpen: () => void }) {
  const text = statusText(service, copy)
  return (
    <button type="button" data-status className="status" title={text} onClick={onOpen}>
      <span
        aria-hidden="true"
        className={`dot ${service === "online" ? "bg-seal" : service === "checking" ? "bg-sidebar-muted" : "bg-warning"}`}
      />
      <span className="lbl" role="status">
        {text}
      </span>
    </button>
  )
}
