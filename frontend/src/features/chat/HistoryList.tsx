/** Recents grouped by date, with rename, copy link, and delete. */

import { useEffect, useId, useRef, useState } from "react"
import { createPortal } from "react-dom"
import type { ChatSummary } from "../../api/chat"
import type { CopyKey } from "../../i18n"
import Icon from "../../shell/icons"
import ConfirmDialog from "../../shell/ConfirmDialog"
import { chatHref, cleanTitle } from "./chatText"
import { clockNow, groupChats } from "./historyGroups"

type Copy = (key: CopyKey) => string

function RenameField({
  title,
  copy,
  onSave,
  onCancel,
}: {
  title: string
  copy: Copy
  onSave: (title: string) => void
  onCancel: () => void
}) {
  const [value, setValue] = useState(title)
  const [invalid, setInvalid] = useState(false)
  const fieldId = useId()

  function save() {
    const next = cleanTitle(value)
    if (!next) {
      setInvalid(true)
      return
    }
    onSave(next)
  }

  return (
    <form
      className="px-1 py-1"
      onSubmit={(event) => {
        event.preventDefault()
        save()
      }}
    >
      <div className="flex min-h-11 items-center gap-1">
        <label htmlFor={fieldId} className="sr-only">
          {copy("renameChat")}
        </label>
        <input
          id={fieldId}
          value={value}
          maxLength={80}
          autoFocus
          onChange={(event) => {
            setValue(event.target.value)
            setInvalid(false)
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault()
              event.stopPropagation()
              onCancel()
            }
          }}
          className="min-w-0 flex-1 bg-transparent px-1 text-sm text-ink outline-none"
        />
        <button
          type="submit"
          aria-label={copy("renameSave")}
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-seal text-seal-ink"
        >
          <Icon name="check" />
        </button>
        <button
          type="button"
          aria-label={copy("renameCancel")}
          onClick={onCancel}
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-muted hover:bg-elevated"
        >
          <Icon name="close" />
        </button>
      </div>
      {invalid ? <p className="px-1 pb-1 text-xs text-low">{copy("titleInvalid")}</p> : null}
    </form>
  )
}

export default function HistoryList({
  chats,
  activeId,
  copy,
  onSelect,
  onRename,
  onDelete,
  onOpenNew,
  onToast,
}: {
  chats: ChatSummary[]
  activeId: string | null
  copy: Copy
  onSelect: (chatId: string) => void
  onRename: (chatId: string, title: string) => Promise<void>
  onDelete: (chatId: string) => Promise<void>
  onOpenNew: () => void
  onToast: (message: string) => void
}) {
  const [menu, setMenu] = useState<{ id: string; top: number; left: number } | null>(null)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<ChatSummary | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const returnFocus = useRef<HTMLElement | null>(null)
  const labels = {
    today: copy("historyToday"),
    yesterday: copy("historyYesterday"),
    week: copy("historyPrevious7"),
  }
  const groups = groupChats(chats, clockNow(), labels)
  const menuChat = chats.find((chat) => chat.id === menu?.id) ?? null

  useEffect(() => {
    if (!menu) return
    function onPointer(event: MouseEvent) {
      const target = event.target as Node
      if (menuRef.current?.contains(target)) return
      if (target instanceof Element && target.closest("[data-history-menu]")) return
      setMenu(null)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return
      event.preventDefault()
      event.stopPropagation()
      setMenu(null)
      returnFocus.current?.focus()
    }
    document.addEventListener("mousedown", onPointer)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onPointer)
      document.removeEventListener("keydown", onKey)
    }
  }, [menu])

  function openMenu(chatId: string, button: HTMLButtonElement) {
    returnFocus.current = button
    if (menu?.id === chatId) {
      setMenu(null)
      return
    }
    const rect = button.getBoundingClientRect()
    const width = 188
    const height = 132
    const left = Math.min(rect.right - width, window.innerWidth - width - 8)
    const top = rect.bottom + height > window.innerHeight ? Math.max(8, rect.top - height) : rect.bottom + 4
    setMenu({ id: chatId, top, left: Math.max(8, left) })
  }

  async function copyLink(chat: ChatSummary) {
    setMenu(null)
    try {
      await navigator.clipboard.writeText(chatHref(chat.id, window.location.href))
      onToast(copy("linkCopied"))
    } catch {
      onToast(copy("linkCopyFailed"))
    }
    returnFocus.current?.focus()
  }

  async function saveTitle(chat: ChatSummary, title: string) {
    setRenamingId(null)
    try {
      await onRename(chat.id, title)
    } catch (error) {
      onToast(error instanceof Error && error.message ? error.message : copy("renameFailed"))
    }
  }

  async function confirmDelete() {
    const chat = pendingDelete
    if (!chat || deletingId) return
    const ids = groups.flatMap((group) => group.chats.map((item) => item.id))
    const nextId = ids[ids.indexOf(chat.id) + 1] ?? null
    const wasActive = chat.id === activeId
    setPendingDelete(null)
    setDeletingId(chat.id)
    try {
      await onDelete(chat.id)
      if (wasActive) onOpenNew()
      window.requestAnimationFrame(() => {
        const target = nextId
          ? document.querySelector<HTMLElement>(`[data-history-id="${CSS.escape(nextId)}"]`)
          : document.querySelector<HTMLElement>("[data-new-chat]")
        target?.focus()
      })
    } catch (error) {
      onToast(error instanceof Error && error.message ? error.message : copy("deleteFailed"))
    } finally {
      setDeletingId(null)
    }
  }

  if (chats.length === 0) {
    return <p className="px-2 py-2 text-sm text-sidebar-muted">{copy("noChats")}</p>
  }

  return (
    <div className="mt-3" aria-label={copy("recentChats")}>
      {groups.map((group) => (
        <section key={group.id} className="mt-3">
          <h2 className="px-2 text-xs text-sidebar-muted">{group.label}</h2>
          <ul className="mt-1">
            {group.chats.map((chat) => {
              const active = chat.id === activeId
              const title = chat.title || copy("newChat")
              const deleting = chat.id === deletingId
              return (
                <li key={chat.id} className={deleting ? "opacity-60" : undefined} aria-busy={deleting}>
                  {renamingId === chat.id ? (
                    <RenameField title={chat.title} copy={copy} onSave={(next) => void saveTitle(chat, next)} onCancel={() => setRenamingId(null)} />
                  ) : (
                    <div className={`group flex min-h-11 min-w-0 items-center rounded-lg ${active ? "bg-mint" : "hover:bg-elevated"}`}>
                      <button
                        type="button"
                        data-history-id={chat.id}
                        title={title}
                        aria-current={active ? "true" : undefined}
                        onClick={() => onSelect(chat.id)}
                        className={`min-w-0 flex-1 truncate px-2 text-left text-sm ${active ? "font-medium text-seal" : ""}`}
                      >
                        {title}
                      </button>
                      {deleting ? (
                        <span className="motion-spin mr-2 inline-block h-3.5 w-3.5 rounded-full border-2 border-rule border-t-seal" aria-hidden="true" />
                      ) : (
                        <button
                          type="button"
                          data-history-menu={chat.id}
                          aria-haspopup="menu"
                          aria-expanded={menu?.id === chat.id}
                          aria-label={`${copy("chatActions")}: ${title}`}
                          onClick={(event) => openMenu(chat.id, event.currentTarget)}
                          className={`mr-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-muted hover:bg-field ${
                            active || menu?.id === chat.id ? "opacity-100" : "opacity-0 focus:opacity-100 group-hover:opacity-100"
                          } group-focus-within:opacity-100`}
                        >
                          <span aria-hidden="true">⋯</span>
                        </button>
                      )}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      ))}
      {menu && menuChat
        ? createPortal(
            <div
              ref={menuRef}
              role="menu"
              aria-label={copy("chatActions")}
              data-motion="rise"
              className="motion-rise fixed z-50 w-44 rounded-xl border border-rule bg-field py-1 shadow-[0_12px_40px_rgba(23,33,29,0.16)]"
              style={{ top: menu.top, left: menu.left }}
            >
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setRenamingId(menuChat.id)
                  setMenu(null)
                }}
                className="flex min-h-10 w-full items-center gap-2 px-3 text-left text-sm hover:bg-elevated"
              >
                <Icon name="pencil" />
                {copy("renameChat")}
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => void copyLink(menuChat)}
                className="flex min-h-10 w-full items-center gap-2 px-3 text-left text-sm hover:bg-elevated"
              >
                <Icon name="link" />
                {copy("copyChatLink")}
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setPendingDelete(menuChat)
                  setMenu(null)
                }}
                className="flex min-h-10 w-full items-center gap-2 px-3 text-left text-sm text-low hover:bg-elevated"
              >
                <Icon name="trash" />
                {copy("deleteChat")}
              </button>
            </div>,
            document.body,
          )
        : null}
      {pendingDelete
        ? createPortal(
            <ConfirmDialog
              title={copy("deleteChatTitle")}
              body={
                <>
                  <span className="text-ink">&quot;{pendingDelete.title || copy("newChat")}&quot;</span> {copy("deleteChatBody")}
                </>
              }
              confirmLabel={copy("deleteChatConfirm")}
              cancelLabel={copy("deleteChatCancel")}
              onCancel={() => {
                setPendingDelete(null)
                returnFocus.current?.focus()
              }}
              onConfirm={() => void confirmDelete()}
            />,
            document.body,
          )
        : null}
    </div>
  )
}
