/** Rebuilds on-screen turns from a saved chat. */

import type { FinalData, StoredMessage } from "../../api/chat"
import { asReplyLanguage } from "../../lib/session"
import { PENDING_PHASES } from "./steps"
import type { Turn } from "./types"

export function orderHistory(messages: StoredMessage[]): StoredMessage[] {
  return messages
    .map((message, index) => ({ message, index }))
    .sort((a, b) => {
      const time = a.message.created_at.localeCompare(b.message.created_at)
      if (time !== 0) return time
      if (a.message.role !== b.message.role) return a.message.role === "user" ? -1 : 1
      return a.index - b.index
    })
    .map((item) => item.message)
}

export function turnsFromHistory(messages: StoredMessage[], corpusDates: Record<string, string>): Turn[] {
  const turns: Turn[] = []
  let question: StoredMessage | null = null
  for (const message of orderHistory(messages)) {
    if (message.role === "user") {
      if (question) turns.push(historyTurn(question, null, corpusDates))
      question = message
    } else if (question) {
      turns.push(historyTurn(question, message, corpusDates))
      question = null
    }
  }
  if (question) turns.push(historyTurn(question, null, corpusDates))
  return turns
}

function historyTurn(
  question: StoredMessage,
  answer: StoredMessage | null,
  corpusDates: Record<string, string>,
): Turn {
  const source = answer?.answer_source
  const confidence = answer?.confidence
  const corpusDate = answer ? answer.corpus_date?.trim() || corpusDates[answer.id] || "" : ""
  const final: FinalData | null =
    answer && (source === "verified" || source === "web" || source === "none")
      ? {
          answer: answer.content,
          answer_source: source,
          confidence: confidence === "high" || confidence === "low" ? confidence : "medium",
          verified: Boolean(answer.verified),
          model: answer.model ?? "",
          tax_year: answer.tax_year ?? "",
          corpus_date: corpusDate,
          action_links: [],
          follow_ups: [],
          cached: false,
          trace: answer.intent
            ? {
                intent: answer.intent,
                search_query: "",
                retrieved: null,
                rerank_top: null,
                verified: answer.verified,
                latency_ms: null,
              }
            : null,
        }
      : null
  return {
    id: question.id,
    question: question.content,
    redacted: false,
    status: "",
    draft: answer?.content ?? "",
    sources: answer?.sources ?? [],
    intent: answer?.intent ?? null,
    detectedLanguage: asReplyLanguage(answer?.language ?? question.language),
    phases: [...PENDING_PHASES],
    queued: false,
    stopped: false,
    replyLanguage: null,
    autoRetryIn: null,
    final,
    error: null,
    messageId: answer?.id ?? null,
    taxYear: answer?.tax_year ?? null,
    feedback: answer?.feedback ?? null,
    feedbackNote: null,
    toolNote: false,
    toolCard: null,
  }
}
