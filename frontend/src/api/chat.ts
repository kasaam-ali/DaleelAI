import { API_URL } from "./client"
import type { Profile, UiLanguage } from "../lib/session"

export type Source = {
  library: "verified" | "web"
  doc_id: string
  title: string
  section: string | null
  page: number | null
  url: string
  mirror_url: string | null
  site: string | null
  fetched_at: string | null
  snippet: string
  rerank_score: number | null
}

export type ActionLink = {
  topic: string
  label: string
  label_ru: string
  url: string
  authority: string
}

export type FinalData = {
  answer: string
  answer_source: "verified" | "web" | "none"
  confidence: "high" | "medium" | "low"
  verified: boolean
  model: string
  tax_year: string
  corpus_date: string
  action_links: ActionLink[]
  follow_ups: string[]
  cached: boolean
  trace?: {
    intent: string
    search_query: string
    retrieved: number | null
    rerank_top: number | null
    verified: boolean | null
    latency_ms: number | null
  } | null
}

export type FeedbackReason = "wrong" | "incomplete" | "outdated" | "other"

export type SseEvent =
  | {
      event: "meta"
      data: {
        chat_id: string
        message_id: string
        intent: string
        language: string
        tax_year: string
      }
    }
  | { event: "token"; data: { text: string } }
  | { event: "sources"; data: { sources: Source[] } }
  | { event: "step"; data: { node: string; status: "start" | "end" } }
  | { event: "verification"; data: { verified: boolean; replaced: boolean } }
  | { event: "final"; data: FinalData }
  | { event: "error"; data: { code: string; message: string } }
  | { event: "done"; data: Record<string, never> }
  | { event: "tool_result"; data: { card: { type: string; data: Record<string, unknown> } } }

export type ChatBody = {
  chat_id: string | null
  message: string
  language: UiLanguage
  tax_year: null
  profile: Profile
}

const KNOWN = new Set([
  "meta",
  "token",
  "sources",
  "step",
  "verification",
  "final",
  "error",
  "done",
  "tool_result",
])

export function parseSseBlock(block: string): SseEvent | null {
  let event = "message"
  const dataLines: string[] = []
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue
    if (line.startsWith("event:")) event = line.slice(6).trim()
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim())
  }
  if (dataLines.length === 0 || !KNOWN.has(event)) return null
  return { event, data: JSON.parse(dataLines.join("\n")) } as SseEvent
}

export function takeSseEvents(buffer: string): { events: SseEvent[]; rest: string } {
  const parts = buffer.replace(/\r\n/g, "\n").split("\n\n")
  const rest = parts.pop() ?? ""
  const events: SseEvent[] = []
  for (const part of parts) {
    if (!part.trim()) continue
    const parsed = parseSseBlock(part)
    if (parsed) events.push(parsed)
  }
  return { events, rest }
}

export async function streamChat(
  body: ChatBody,
  sessionId: string,
  onEvent: (event: SseEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      "X-Session-Id": sessionId,
    },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok || !response.body) {
    throw new Error(await errorMessage(response))
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const taken = takeSseEvents(buffer)
    buffer = taken.rest
    for (const event of taken.events) onEvent(event)
  }
  buffer += decoder.decode()
  const tail = takeSseEvents(`${buffer}\n\n`)
  for (const event of tail.events) onEvent(event)
}

export async function sendFeedback(
  sessionId: string,
  messageId: string,
  rating: "up" | "down",
  reason: FeedbackReason | null,
): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": sessionId,
    },
    body: JSON.stringify({
      message_id: messageId,
      rating,
      reason,
      comment: null,
      share_conversation: false,
    }),
  })
  if (!response.ok) throw new Error(await errorMessage(response))
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { message?: string }; detail?: unknown }
    if (body.error?.message) return body.error.message
  } catch {
    /* response was not JSON */
  }
  return `Request failed (${response.status})`
}

export type ChatSummary = {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export type StoredMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  intent: string | null
  language: string | null
  tax_year: string | null
  sources: Source[]
  answer_source: "verified" | "web" | "none" | null
  confidence: "high" | "medium" | "low" | null
  verified: boolean | null
  model: string | null
  created_at: string
  feedback: "up" | "down" | null
  feedback_reason: FeedbackReason | null
}

export type ChatDetail = ChatSummary & {
  messages: StoredMessage[]
}

export async function listChats(sessionId: string): Promise<ChatSummary[]> {
  const response = await fetch(`${API_URL}/api/v1/chats`, {
    headers: { "X-Session-Id": sessionId },
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  const body = (await response.json()) as { chats: ChatSummary[] }
  return body.chats
}

export async function getChat(sessionId: string, chatId: string): Promise<ChatDetail> {
  const response = await fetch(`${API_URL}/api/v1/chats/${chatId}`, {
    headers: { "X-Session-Id": sessionId },
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  return (await response.json()) as ChatDetail
}
