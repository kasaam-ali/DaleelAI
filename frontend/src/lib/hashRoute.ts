/** Reads the hash route. A copied chat link looks like #/chat/<uuid>. */

export const VIEWS = [
  "home",
  "chat",
  "calculator",
  "filer",
  "notice",
  "checklist",
  "experts",
  "updates",
  "evaluation",
  "privacy",
] as const

export type AppView = (typeof VIEWS)[number]

const CHAT_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function parseHash(hash: string): { view: AppView; chatId: string | null } {
  const body = hash.replace(/^#\/?/, "")
  const [head, rest] = body.split("/")
  const view = VIEWS.includes(head as AppView) ? (head as AppView) : "home"
  const chatId = head === "chat" && rest && CHAT_ID.test(rest) ? rest : null
  return { view: chatId ? "chat" : view, chatId }
}
