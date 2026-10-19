/** Which refusal card a finished answer should use. */

export type RefusalKind = "evidence" | "scope" | "declined" | "provincial"

export function refusalKind(
  intent: string | null,
  answerSource: string | null | undefined,
): RefusalKind | null {
  if (intent === "refuse") return "declined"
  if (intent === "out_of_scope" || intent === "chitchat") return "scope"
  if (intent === "provincial") return "provincial"
  if (intent === "qa" && answerSource === "none") return "evidence"
  return null
}
