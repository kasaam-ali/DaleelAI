/** Trust badge, source count and up to four source cards (2×2 while the panel is open). */

import type { FinalData, Source } from "../../../api/chat"
import SourceCard from "./SourceCard"
import TrustBadge from "./TrustBadge"
import { fill } from "./refs"
import type { Copy, OpenSource } from "./types"

export default function SourcesStrip({
  sources,
  final,
  cited,
  turnId,
  activeCite,
  copy,
  onOpen,
}: {
  sources: Source[]
  final: FinalData | null
  cited: boolean
  turnId: string
  activeCite: number | null
  copy: Copy
  onOpen: OpenSource
}) {
  const library = sources.filter((source) => source.library !== "web").length
  const web = sources.length - library
  const count = [
    library === 1 ? copy("oneSourceCount") : library > 1 ? fill(copy("nSources"), { n: library }) : "",
    web > 0 ? fill(copy("nWeb"), { n: web }) : "",
  ]
    .filter(Boolean)
    .join(" + ")
  return (
    <section data-motion-slot="sources-strip" aria-label={copy("sources")} className="strip-wrap">
      <div className="strip-head">
        <TrustBadge final={final} cited={cited} copy={copy} />
        {count ? <span className="count">{count}</span> : null}
      </div>
      {sources.length > 0 ? (
        <div className="strip">
          {sources.slice(0, 4).map((source, index) => (
            <SourceCard
              key={`${source.doc_id}-${index}`}
              n={index + 1}
              index={index}
              source={source}
              turnId={turnId}
              active={activeCite === index + 1}
              copy={copy}
              onOpen={onOpen}
            />
          ))}
        </div>
      ) : null}
    </section>
  )
}
