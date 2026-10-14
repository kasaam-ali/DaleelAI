import type { FinalData, Source } from "../../api/chat"

export type Turn = {
  id: string
  question: string
  redacted: boolean
  status: string
  draft: string
  sources: Source[]
  final: FinalData | null
  error: string | null
  messageId: string | null
  taxYear: string | null
  feedback: "up" | "down" | null
  feedbackNote: string | null
  toolNote: boolean
  toolCard: { type: string; data: Record<string, unknown> } | null
}
