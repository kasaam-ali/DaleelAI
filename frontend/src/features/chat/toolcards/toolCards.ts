/** Which tool_result types have a PR 5b card, and which of them hide the duplicate answer text. */

export const CARD_TYPES = new Set(["filer_comparison", "notice", "checklist", "experts", "updates"])

/** The notice and experts cards already say what the answer says. */
export const HIDES_ANSWER = new Set(["notice", "experts"])
