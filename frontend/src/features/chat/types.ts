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
  stopped: boolean
  replyLanguage: "en" | "roman_urdu" | null
  autoRetryIn: number | null
  /** The person cancelled auto-retry on this error; Retry now stays. */
  autoRetryCancelled: boolean
  /** When the question went out (ms), and each step's finish time in seconds since then. */
  sentAt: number | null
  phaseTimes: (number | null)[]
  final: FinalData | null
  error: TurnError | null
  messageId: string | null
  taxYear: string | null
  feedback: "up" | "down" | null
  feedbackNote: string | null
  toolNote: boolean
  toolCard: { type: string; data: Record<string, unknown> } | null
}
