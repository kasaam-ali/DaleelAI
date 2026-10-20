/** Sidebar brand. In the chat sidebar it is a link back to Home (handoff-pr18-nav.md §4.1). */

import type { CopyKey } from "../i18n"
import { inAppClick } from "./navEvents"
import Icon from "./icons"

type Copy = (key: CopyKey) => string

function Mark() {
  return (
    <span className="mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 5.5h7.2L17 9.2V18.5H6v-13z" />
        <path d="M13 5.5V9h4" />
      </svg>
    </span>
  )
}

export default function Brand({
  copy,
  homeLink,
  sidebarId,
  rail,
  onHome,
  onCollapse,
}: {
  copy: Copy
  homeLink: boolean
  sidebarId: string
  rail: boolean
  onHome: () => void
  onCollapse: () => void
}) {
  const inner = (
    <>
      <Mark />
      <span className="lbl">
        <b>DaleelAI</b>
        <small>{copy("subtitle")}</small>
      </span>
    </>
  )
  return (
    <div className="brand">
      {homeLink ? (
        <a href="#/" data-brand-home className="brand-home" title={copy("backHome")} onClick={(event) => inAppClick(event, onHome)}>
          {inner}
          <span className="sr-only"> · {copy("backHome")}</span>
        </a>
      ) : (
        inner
      )}
      <button
        type="button"
        className="iconbtn sb-collapse only-desk"
        aria-label={copy("collapseSidebar")}
        title={copy("collapseSidebar")}
        aria-expanded={!rail}
        aria-controls={sidebarId}
        onClick={onCollapse}
      >
        <Icon name="panelLeft" />
      </button>
    </div>
  )
}
