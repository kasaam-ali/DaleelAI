/** A source card in the strip: [n] ref, document, page (library) or domain and check date (web). */

import type { CSSProperties } from "react"
import type { Source } from "../../../api/chat"
import Icon from "../../../shell/icons"
import { docShort, fill, formatDate, fullRef, sectionRef, siteOf } from "./refs"
import { panelId, type Copy, type OpenSource } from "./types"

export default function SourceCard({
  n,
  source,
  turnId,
  active,
  index,
  copy,
  onOpen,
}: {
  n: number
  source: Source
  turnId: string
  active: boolean
  index: number
  copy: Copy
  onOpen: OpenSource
}) {
  const web = source.library === "web"
  return (
    <button
      type="button"
      className={`src${web ? " webs" : ""}${active ? " on" : ""}`}
      style={{ "--i": index } as CSSProperties}
      data-cite={n}
      aria-pressed={active}
      aria-controls={panelId(turnId)}
      aria-label={fill(copy("sourceChipName"), { n, ref: fullRef(source) })}
      onClick={(event) => onOpen(n, event.currentTarget)}
    >
      <span className="src-top">
        {web ? <Icon name="globe" size="sm" /> : <span className="tag">{n}</span>}
        <span className="src-ref" dir="ltr">
          {web ? siteOf(source) : sectionRef(source)}
        </span>
      </span>
      <span className="src-sub">{source.title}</span>
      <span className="src-pg">
        {web ? (
          fill(copy("checkedOn"), { date: formatDate(source.fetched_at) })
        ) : (
          <>
            <Icon name="pdf" size="sm" />
            {source.page != null ? `${copy("pageShort")}${source.page} · ` : ""}
            {docShort(source)}
          </>
        )}
      </span>
    </button>
  )
}
