/** Maps pipeline nodes onto the four loading steps. */

export type StepStatus = "pending" | "active" | "done"

const PHASE_NODES: readonly (readonly string[])[] = [
  ["rewrite"],
  ["retrieve", "rerank", "expand", "web_fallback", "sufficiency"],
  ["generate"],
  ["verify", "links"],
]

export const PENDING_PHASES: StepStatus[] = ["pending", "pending", "pending", "pending"]

export function reducePhases(current: StepStatus[], node: string, status: "start" | "end"): StepStatus[] {
  const index = PHASE_NODES.findIndex((nodes) => nodes.includes(node))
  if (index < 0) return current
  return current.map((phase, position) => {
    if (status === "start") {
      if (position < index) return "done"
      if (position === index) return "active"
      return phase
    }
    if (position === index && phase === "active") return "done"
    return phase
  })
}
