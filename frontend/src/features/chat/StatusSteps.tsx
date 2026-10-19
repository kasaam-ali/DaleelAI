/** Loading steps and the skeleton that sits under them. */

import type { CopyKey } from "../../i18n"
import type { StepStatus } from "./steps"

type Copy = (key: CopyKey) => string

const LABELS = ["stepUnderstand", "stepLibrary", "stepWrite", "stepCheck"] as const

function Mark({ status }: { status: StepStatus }) {
  if (status === "done") return <span aria-hidden="true" className="mt-0.5 text-seal">✓</span>
  if (status === "active") {
    return (
      <span
        aria-hidden="true"
        className="mt-1 inline-block h-3 w-3 animate-spin rounded-full border-2 border-seal border-t-transparent"
      />
    )
  }
  return <span aria-hidden="true" className="mt-1 inline-block h-3 w-3 rounded-full border border-rule" />
}

export default function StatusSteps({ phases, copy }: { phases: StepStatus[]; copy: Copy }) {
  return (
    <div data-motion-slot="status-steps">
      <p className="text-sm font-medium text-ink">{copy("checkingLibrary")}</p>
      <ol className="mt-3 grid gap-2" aria-busy={phases.includes("active")}>
        {LABELS.map((label, index) => {
          const status = phases[index] ?? "pending"
          return (
            <li key={label} className="flex items-start gap-2 text-sm">
              <Mark status={status} />
              <span>
                {copy(label)}
                {index === 1 && status === "active" ? (
                  <span className="block text-xs text-muted">{copy("stepLibrarySub")}</span>
                ) : null}
              </span>
            </li>
          )
        })}
      </ol>
      <div className="mt-4 grid grid-cols-4 gap-2" aria-hidden="true">
        {LABELS.map((label) => (
          <div key={label} className="waiting h-16" />
        ))}
      </div>
      <div className="mt-3 grid gap-2" aria-hidden="true">
        <div className="waiting h-4 w-4/5" />
        <div className="waiting h-4 w-full" />
        <div className="waiting h-4 w-2/3" />
      </div>
    </div>
  )
}
