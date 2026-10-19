/** The shape of one question and its answer on screen. */

import type { FinalData, Source } from "../../api/chat"
import type { TurnError } from "./failure"
import type { StepStatus } from "./steps"

export type Turn = {
  id: string
  question: string
  redacted: boolean
  status: string
  draft: string
  sources: Source[]
  intent: string | null
  detectedLanguage: "en" | "roman_urdu" | null
  phases: StepStatus[]
  queued: boolean
  autoRetryIn: number | null
  final: FinalData | null
  error: TurnError | null
  messageId: string | null
  taxYear: string | null
  feedback: "up" | "down" | null
  feedbackNote: string | null
  toolNote: boolean
  toolCard: { type: string; data: Record<string, unknown> } | null
}
