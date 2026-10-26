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

/** Nav v2 hash routes (handoff-pr18-nav.md §1) that name an existing view differently. */
const ALIASES: Record<string, AppView> = { about: "privacy", checklists: "checklist" }
const HASHES: Partial<Record<AppView, string>> = { privacy: "about", checklist: "checklists" }

/** The hash a view is written to: `#/about`, `#/checklists`, `#/calculator`; Home is empty. */
export function hashFor(view: AppView): string {
  return view === "home" ? "" : `#/${HASHES[view] ?? view}`
}

export function parseHash(hash: string): { view: AppView; chatId: string | null } {
  const body = hash.replace(/^#\/?/, "")
  const [rawHead, rest] = body.split("/")
  const head = ALIASES[rawHead] ?? rawHead
  const view = VIEWS.includes(head as AppView) ? (head as AppView) : "home"
  const chatId = head === "chat" && rest && CHAT_ID.test(rest) ? rest : null
  return { view: chatId ? "chat" : view, chatId }
}
