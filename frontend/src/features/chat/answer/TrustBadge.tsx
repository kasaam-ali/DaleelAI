/** One trust badge per answer (SPEC §9): checking, verified library, official website, or no source. */

import type { FinalData } from "../../../api/chat"
import Icon from "../../../shell/icons"
import type { Copy } from "./types"

const CONFIDENCE = { high: "trustHigh", medium: "trustMedium", low: "trustLow" } as const

export default function TrustBadge({ final, cited, copy }: { final: FinalData | null; cited: boolean; copy: Copy }) {
  if (!final) {
    return (
      <span className="badge checking" data-trust="checking">
        <Icon name="refresh" size="sm" />
        {copy("checkingSources")}
      </span>
    )
  }
  const library = cited ? final.answer_source : "none"
  if (library === "none") {
    return (
      <span className="badge none" data-trust="none">
        <Icon name="info" size="sm" />
        {copy("libraryNone")}
      </span>
    )
  }
  const web = library === "web"
  return (
    <span className={`badge ${web ? "webb" : "verified"}`} data-trust={library}>
      <Icon name={web ? "globe" : "checkShield"} size="sm" />
      {copy(web ? "libraryWeb" : "libraryVerified")} · {copy(CONFIDENCE[final.confidence])}
    </span>
  )
}
