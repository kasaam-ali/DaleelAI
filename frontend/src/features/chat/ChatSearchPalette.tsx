/** Ctrl K search across chat titles and cached answer snippets. */

import { useId, useRef, useState, type ReactNode } from "react"
import type { ChatSummary } from "../../api/chat"
import type { CopyKey } from "../../i18n"
import Icon from "../../shell/icons"
import { useModal } from "../../shell/useModal"
import type { TextRange } from "./chatText"
import { searchChats } from "./chatText"
import { clockNow, historyLabel } from "./historyGroups"

type Copy = (key: CopyKey) => string

function Highlight({ text, ranges }: { text: string; ranges: TextRange[] }) {
  if (!text) return null
  if (ranges.length === 0) return <>{text}</>
  const parts: ReactNode[] = []
  let cursor = 0
  ranges.forEach((range, index) => {
    if (range.start > cursor) parts.push(text.slice(cursor, range.start))
    parts.push(
      <mark key={`${range.start}-${index}`} className="chat-hit">
        {text.slice(range.start, range.end)}
      </mark>,
    )
    cursor = range.end
  })
  if (cursor < text.length) parts.push(text.slice(cursor))
  return <>{parts}</>
}

export default function ChatSearchPalette({
  chats,
  snippets,
  copy,
  onOpen,
  onClose,
}: {
  chats: ChatSummary[]
  snippets: Record<string, string>
  copy: Copy
  onOpen: (chatId: string) => void
  onClose: () => void
}) {
  const [query, setQuery] = useState("")
  const [active, setActive] = useState(0)
  const panelRef = useRef<HTMLDivElement>(null)
  const listId = useId()
  const labels = {
    today: copy("historyToday"),
    yesterday: copy("historyYesterday"),
    week: copy("historyPrevious7"),
  }
  const [trackedQuery, setTrackedQuery] = useState(query)
  if (query !== trackedQuery) {
    setTrackedQuery(query)
    setActive(0)
  }
  const hits = searchChats(chats, snippets, query)
  const current = hits[Math.min(active, Math.max(hits.length - 1, 0))]
  useModal(true, panelRef, onClose)

  function choose(index: number) {
    const hit = hits[index]
    if (!hit) return
    onOpen(hit.chat.id)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[12vh]">
      <div className="motion-scrim absolute inset-0 bg-ink/45" onClick={onClose} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={copy("searchChats")}
        data-motion="rise"
        className="motion-rise relative flex max-h-[min(32rem,70vh)] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-rule bg-field shadow-[0_12px_40px_rgba(23,33,29,0.16)]"
      >
        <div className="flex items-center gap-2 border-b border-rule px-3">
          <span className="text-muted">
            <Icon name="search" />
          </span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={copy("searchPlaceholder")}
            aria-controls={listId}
            aria-activedescendant={current ? `${listId}-${current.chat.id}` : undefined}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault()
                setActive((index) => Math.min(index + 1, Math.max(hits.length - 1, 0)))
              } else if (event.key === "ArrowUp") {
                event.preventDefault()
                setActive((index) => Math.max(index - 1, 0))
              } else if (event.key === "Enter") {
                event.preventDefault()
                choose(active)
              }
            }}
            className="min-h-12 w-full bg-transparent text-base text-ink outline-none"
          />
          <button type="button" onClick={onClose} className="rounded-lg border border-rule px-2 py-1 text-xs text-muted">
            Esc
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
          <p className="px-2 pb-1 text-[11px] tracking-[0.06em] text-muted uppercase">{copy("searchLabel")}</p>
          {hits.length === 0 ? (
            <p className="px-2 py-6 text-sm text-muted">{copy("searchEmpty")}</p>
          ) : (
            <ul id={listId} role="listbox" aria-label={copy("searchLabel")}>
              {hits.map((hit, index) => {
                const selected = index === active
                return (
                  <li key={hit.chat.id}>
                    <button
                      type="button"
                      id={`${listId}-${hit.chat.id}`}
                      role="option"
                      aria-selected={selected}
                      tabIndex={-1}
                      onMouseEnter={() => setActive(index)}
                      onClick={() => choose(index)}
                      className={`flex w-full items-start gap-3 rounded-xl px-2 py-2 text-left ${selected ? "bg-mint" : "hover:bg-elevated"}`}
                    >
                      <span className="mt-0.5 text-muted">
                        <Icon name="chat" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-ink">
                          <Highlight text={hit.chat.title || copy("newChat")} ranges={hit.titleRanges} />
                        </span>
                        {hit.snippet ? (
                          <span className="mt-0.5 block truncate text-xs text-muted">
                            <Highlight text={hit.snippet} ranges={hit.snippetRanges} />
                          </span>
                        ) : null}
                      </span>
                      <span className="shrink-0 pt-0.5 text-xs text-muted">
                        {historyLabel(hit.chat.updated_at, clockNow(), labels)}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
        <p className="flex flex-wrap gap-x-4 gap-y-1 border-t border-rule px-3 py-2 text-xs text-muted">
          <span>
            <kbd className="font-medium text-ink">↑↓</kbd> {copy("searchMove")}
          </span>
          <span>
            <kbd className="font-medium text-ink">Enter</kbd> {copy("searchOpenKey")}
          </span>
          <span>
            <kbd className="font-medium text-ink">Esc</kbd> {copy("searchCloseKey")}
          </span>
        </p>
      </div>
    </div>
  )
}
