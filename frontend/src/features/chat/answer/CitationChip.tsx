/** An inline [n] chip that opens source n in the panel (SPEC §5.2A item 5). */

import type { Source } from "../../../api/chat"
import { fill, fullRef } from "./refs"
import { panelId, type Copy, type OpenSource } from "./types"

export default function CitationChip({
  n,
  source,
  turnId,
  active,
  copy,
  onOpen,
}: {
  n: number
  source: Source
  turnId: string
  active: boolean
  copy: Copy
  onOpen: OpenSource
}) {
  return (
    <button
      type="button"
      className={`cite${active ? " on" : ""}`}
      data-cite={n}
      aria-pressed={active}
      aria-controls={panelId(turnId)}
      aria-label={fill(copy("sourceChipName"), { n, ref: fullRef(source) })}
      onClick={(event) => onOpen(n, event.currentTarget)}
    >
      {n}
    </button>
  )
}
