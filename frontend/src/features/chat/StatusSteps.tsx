/** Loading steps (SPEC §5.2A item 3, §6): a card with 4 steps and a connector, then the skeleton strip + lines. */

import type { CSSProperties } from "react"
import type { CopyKey } from "../../i18n"
import Icon from "../../shell/icons"
import type { StepStatus } from "./steps"

type Copy = (key: CopyKey) => string

const LABELS = ["stepUnderstand", "stepLibrary", "stepWrite", "stepCheck"] as const
/** Sub-labels we can show from what the stream carries today (no counts yet). */
const DETAIL: Partial<Record<number, CopyKey>> = { 1: "stepLibrarySub" }

export default function StatusSteps({
  phases,
  times = [],
  copy,
  skeleton = true,
}: {
  phases: StepStatus[]
  times?: (number | null)[]
  copy: Copy
  skeleton?: boolean
}) {
  const writing = phases[2] !== "pending"
  const busy = phases.some((phase) => phase !== "done")
  return (
    <div data-motion-slot="status-steps" className="st-wrap">
      {busy ? (
        <p className="working">
          <span className="orb" aria-hidden="true" />
          {copy(writing ? "writingAnswer" : "checkingLibrary")}
        </p>
      ) : null}
      <ol className="psteps" aria-busy={busy}>
        {LABELS.map((label, index) => {
          const status = phases[index] ?? "pending"
          const cls = status === "done" ? "done" : status === "active" ? "act" : "todo"
          const detail = DETAIL[index]
          const time = times[index]
          return (
            <li key={label} className={cls} data-step={status} style={{ "--i": index } as CSSProperties}>
              <span className="s" aria-hidden="true">
                {status === "done" ? <Icon name="check" size="sm" /> : null}
              </span>
              <span>
                <b>{copy(label)}</b>
                {status !== "pending" && detail ? <small>{copy(detail)}</small> : null}
              </span>
              <span className="t">{status === "done" && time != null ? `${time.toFixed(1)}s` : ""}</span>
            </li>
          )
        })}
      </ol>
      {skeleton ? (
        <div aria-hidden="true">
          <div className="sk-strip">
            {LABELS.map((label) => (
              <div key={label} className="sk" />
            ))}
          </div>
          <div className="sk" style={{ width: "90%" }} />
          <div className="sk" />
          <div className="sk" style={{ width: "65%" }} />
        </div>
      ) : null}
    </div>
  )
}
