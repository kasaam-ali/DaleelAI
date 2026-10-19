/** Small pure helpers for titles, snippets, search highlights, and chat links. */

import type { ChatSummary } from "../../api/chat"

export type TextRange = { start: number; end: number }

export type SearchHit = {
  chat: ChatSummary
  snippet: string
  titleRanges: TextRange[]
  snippetRanges: TextRange[]
}

export function cleanTitle(value: string): string | null {
  if (/[\r\n]/.test(value)) return null
  const title = value.trim()
  if (title.length < 1 || title.length > 80) return null
  return title
}

export function chatHref(chatId: string, href: string): string {
  const url = new URL(href)
  url.hash = `#/chat/${chatId}`
  return url.toString()
}

export function assistantSnippet(messages: { role: string; content: string }[]): string {
  const assistant = [...messages].reverse().find((message) => message.role === "assistant")
  return (assistant?.content ?? "").replace(/\s+/g, " ").trim().slice(0, 180)
}

export function findRanges(text: string, query: string): TextRange[] {
  const needle = query.trim().toLowerCase()
  if (!needle) return []
  const hay = text.toLowerCase()
  const ranges: TextRange[] = []
  let from = 0
  while (from < hay.length) {
    const at = hay.indexOf(needle, from)
    if (at < 0) break
    ranges.push({ start: at, end: at + needle.length })
    from = at + needle.length
  }
  return ranges
}

export function searchChats(chats: ChatSummary[], snippets: Record<string, string>, query: string): SearchHit[] {
  const needle = query.trim()
  const sorted = [...chats].sort((a, b) => (a.updated_at < b.updated_at ? 1 : a.updated_at > b.updated_at ? -1 : 0))
  const hits: SearchHit[] = []
  for (const chat of sorted) {
    const snippet = snippets[chat.id] ?? ""
    const titleRanges = findRanges(chat.title, needle)
    const snippetRanges = findRanges(snippet, needle)
    if (needle && titleRanges.length === 0 && snippetRanges.length === 0) continue
    hits.push({ chat, snippet, titleRanges, snippetRanges })
  }
  return hits
}
