/** "How this was answered": KPI tiles, trace steps, model and latency. The only place the model name shows. */

import type { CSSProperties } from "react"
import type { FinalData } from "../../../api/chat"
import Icon from "../../../shell/icons"
import { fill } from "./refs"
import type { Copy } from "./types"

export default function HowAnswered({
  final,
  kept,
  cited,
  copy,
}: {
  final: FinalData
  /** Library passages the answer was written from. */
  kept: number
  /** Distinct [n] markers in the answer that point at a source. */
  cited: number
  copy: Copy
}) {
  const trace = final.trace
  const retrieved = trace?.retrieved ?? null
  const verifiedCount = final.verified && trace?.verified !== false ? cited : 0
  const tiles: { label: string; value: string; fill: number }[] = []
  if (retrieved != null) tiles.push({ label: copy("howPassages"), value: String(retrieved), fill: 1 })
  if (retrieved != null) tiles.push({ label: copy("howKept"), value: String(kept), fill: retrieved ? kept / retrieved : 0 })
  if (cited > 0) {
    tiles.push({
      label: copy("howVerified"),
      value: fill(copy("howOf"), { a: verifiedCount, b: cited }),
      fill: verifiedCount / cited,
    })
  }
  const steps = [
    trace?.search_query ? fill(copy("howStepQuery"), { q: trace.search_query }) : null,
    retrieved != null ? copy("howStepSearch") : null,
    trace?.rerank_top != null ? fill(copy("howStepRerank"), { s: trace.rerank_top.toFixed(2) }) : null,
    final.verified && trace?.verified !== false ? copy("howStepVerify") : null,
  ].filter((step): step is string => Boolean(step))
  const model = final.model && final.model !== "none" ? final.model : null
  const seconds = trace?.latency_ms != null ? (trace.latency_ms / 1000).toFixed(1) : null

  return (
    <details className="how2" data-how-answered>
      <summary>
        <Icon name="info" size="sm" />
        {copy("howAnswered")}
        <Icon name="chev" size="sm" className="chev" />
      </summary>
      {tiles.length > 0 ? (
        <div className="grid" style={{ "--cols": tiles.length } as CSSProperties}>
          {tiles.map((tile) => (
            <div key={tile.label} className="k">
              <span>{tile.label}</span>
              <b>{tile.value}</b>
              <i aria-hidden="true">
                <em style={{ transform: `scaleX(${Math.max(0, Math.min(1, tile.fill))})` }} />
              </i>
            </div>
          ))}
        </div>
      ) : null}
      {steps.length > 0 ? (
        <ol>
          {steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      ) : null}
      {model ? (
        <p className="model" data-model>
          {seconds ? fill(copy("howModel"), { m: model, s: seconds }) : `Model ${model}`}
        </p>
      ) : null}
    </details>
  )
}
