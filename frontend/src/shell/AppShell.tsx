/** Sidebar, top bar, and the frame around every page. */

import { useEffect, useId, useRef, useState, type ReactNode } from "react"
import type { ChatSummary } from "../api/chat"
import type { CopyKey } from "../i18n"
import ProfilePanel from "../features/onboarding/ProfilePanel"
import type { Profile, Theme, UiLanguage } from "../lib/session"
import Icon, { type IconName } from "./icons"

export type AppView =
  | "home"
  | "chat"
  | "calculator"
  | "filer"
  | "notice"
  | "checklist"
  | "experts"
  | "updates"
  | "evaluation"
  | "privacy"

type Copy = (key: CopyKey) => string

function HeaderMenu({
  label,
  trigger,
  options,
}: {
  label: string
  trigger: ReactNode
  options: { id: string; label: string; selected: boolean; onSelect: () => void }[]
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    function onPointer(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener("mousedown", onPointer)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onPointer)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label}
        title={label}
        onClick={() => setOpen((current) => !current)}
        className="inline-flex h-11 items-center gap-1.5 px-2 text-sm text-ink hover:bg-elevated"
      >
        {trigger}
      </button>
      {open ? (
        <div role="menu" aria-label={label} className="absolute right-0 z-20 mt-1 min-w-40 border border-rule bg-field py-1">
          {options.map((option) => (
            <button
              key={option.id}
              type="button"
              role="menuitemradio"
              aria-checked={option.selected}
              onClick={() => {
                option.onSelect()
                setOpen(false)
                buttonRef.current?.focus()
              }}
              className={`flex min-h-11 w-full items-center px-3 text-left text-sm hover:bg-elevated ${
                option.selected ? "font-medium text-seal" : ""
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

const TOOLS: { id: AppView; label: CopyKey; icon: IconName }[] = [
  { id: "calculator", label: "navCalculator", icon: "calculator" },
  { id: "filer", label: "navFiler", icon: "filer" },
  { id: "notice", label: "navNotice", icon: "notice" },
  { id: "checklist", label: "navChecklist", icon: "checklist" },
  { id: "experts", label: "navExperts", icon: "experts" },
  { id: "updates", label: "navUpdates", icon: "updates" },
  { id: "evaluation", label: "navEvaluation", icon: "evaluation" },
]

export default function AppShell({
  view,
  language,
  theme,
  profile,
  chats,
  activeChatId,
  service,
  menuOpen,
  copy,
  onView,
  onNewChat,
  onSelectChat,
  onClearHistory,
  onLanguage,
  onTheme,
  onProfile,
  onMenu,
  children,
}: {
  view: AppView
  language: UiLanguage
  theme: Theme
  profile: Profile
  chats: ChatSummary[]
  activeChatId: string | null
  service: "checking" | "online" | "degraded" | "offline"
  menuOpen: boolean
  copy: Copy
  onView: (view: AppView) => void
  onNewChat: () => void
  onSelectChat: (chatId: string) => void
  onClearHistory: () => void
  onLanguage: (language: UiLanguage) => void
  onTheme: () => void
  onProfile: (patch: Partial<Profile>) => void
  onMenu: (open: boolean) => void
  children: ReactNode
}) {
  const sidebarId = useId()
  const sidebarRef = useRef<HTMLElement>(null)
  const [collapsed, setCollapsed] = useState(false)
  const [confirmClear, setConfirmClear] = useState(false)
  const cancelClearRef = useRef<HTMLButtonElement>(null)
  const title =
    view === "home"
      ? copy("navHome")
      : view === "chat"
        ? (chats.find((chat) => chat.id === activeChatId)?.title ?? copy("navChatItem"))
        : copy(TOOLS.find((item) => item.id === view)?.label ?? (view === "privacy" ? "navPrivacy" : "navHome"))

  useEffect(() => {
    if (!menuOpen) return
    const root = sidebarRef.current
    if (!root) return
    const focusable = () =>
      Array.from(
        root.querySelectorAll<HTMLElement>("button, a, input, select, textarea, [tabindex]"),
      ).filter((element) => !element.hasAttribute("disabled") && element.tabIndex !== -1)
    focusable()[0]?.focus()

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onMenu(false)
        return
      }
      if (event.key !== "Tab") return
      const items = focusable()
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [menuOpen, onMenu])

  useEffect(() => {
    if (!confirmClear) return
    cancelClearRef.current?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setConfirmClear(false)
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [confirmClear])

  function choose(next: AppView) {
    onView(next)
    onMenu(false)
  }

  function pickTheme(next: Theme) {
    if (next !== theme) onTheme()
  }

  return (
    <div className="flex h-dvh bg-paper text-ink" data-drawer={menuOpen ? "open" : "closed"}>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:inline-flex focus:min-h-11 focus:items-center focus:bg-field focus:px-3 focus:text-ink"
      >
        {copy("skipToQuestion")}
      </a>
      {menuOpen ? (
        <button
          type="button"
          aria-label={copy("closeMenu")}
          className="fixed inset-0 z-30 bg-ink/40 lg:hidden"
          onClick={() => onMenu(false)}
        />
      ) : null}
      <aside
        id={sidebarId}
        ref={sidebarRef}
        className={`fixed inset-y-0 left-0 z-40 flex w-[272px] flex-col overflow-hidden border-r border-rule bg-sidebar text-sidebar-ink transition-[transform,width] duration-200 ease-out lg:static lg:translate-x-0 ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        } ${collapsed ? "lg:w-[76px]" : "lg:w-[248px]"}`}
      >
        <div className={`flex items-center gap-3 px-4 pt-5 ${collapsed ? "lg:justify-center lg:px-2" : ""}`}>
          <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-seal text-seal-ink" aria-hidden="true">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M6 5.5h7.2L17 9.2V18.5H6v-13z" strokeLinejoin="round" />
              <path d="M13 5.5V9h4" strokeLinejoin="round" />
            </svg>
          </span>
          <div className={collapsed ? "lg:sr-only" : ""}>
            <p className="font-statute text-[1.65rem] leading-none tracking-tight">DaleelAI</p>
            <p className="mt-1 text-xs text-sidebar-muted">{copy("subtitle")}</p>
          </div>
        </div>
        <nav className={`sidebar-scroll mt-4 min-h-0 flex-1 overflow-y-auto px-2 ${collapsed ? "lg:px-1" : ""}`} aria-label={copy("product")}>
          <details className={collapsed ? "lg:hidden" : ""}>
            <summary className="min-h-11 cursor-pointer list-none px-2 py-2 text-sm">
              {copy("profileTitle")}
              <span className="mt-1 block text-xs leading-snug text-sidebar-muted">{copy("profileHelp")}</span>
            </summary>
            <ProfilePanel profile={profile} copy={copy} onChange={onProfile} compact />
          </details>
          <button
            type="button"
            title={copy("profileTitle")}
            aria-label={copy("profileTitle")}
            onClick={() => setCollapsed(false)}
            className={`mb-1 hidden min-h-11 w-full items-center justify-center px-2 hover:bg-elevated ${
              collapsed ? "lg:inline-flex" : ""
            }`}
          >
            <Icon name="filing" />
          </button>
          <div className="mt-3 grid gap-1">
          <p className={`px-2 pb-1 text-xs text-sidebar-muted ${collapsed ? "lg:sr-only" : ""}`}>{copy("groupPrimary")}</p>
          <button
            type="button"
            title={copy("navHome")}
            aria-current={view === "home" ? "page" : undefined}
            onClick={() => choose("home")}
            className={`flex min-h-11 items-center gap-2 px-2 text-left text-sm hover:bg-elevated ${
              view === "home" ? "bg-mint font-medium text-seal" : ""
            } ${collapsed ? "lg:justify-center" : ""}`}
          >
            <Icon name="home" />
            <span className={collapsed ? "lg:sr-only" : ""}>{copy("navHome")}</span>
          </button>
          <button
            type="button"
            title={copy("newChat")}
            onClick={() => {
              onNewChat()
              onMenu(false)
            }}
            className={`flex min-h-11 items-center gap-2 px-2 text-left text-sm hover:bg-elevated ${
              collapsed ? "lg:justify-center" : ""
            }`}
          >
            <Icon name="plus" />
            <span className={collapsed ? "lg:sr-only" : ""}>{copy("newChat")}</span>
          </button>
          </div>
          <div className="mt-3">
          <p className={`px-2 text-xs text-sidebar-muted ${collapsed ? "lg:sr-only" : ""}`}>{copy("recentChats")}</p>
          {chats.length === 0 ? (
            <p className={`px-2 py-2 text-sm text-sidebar-muted ${collapsed ? "lg:hidden" : ""}`}>{copy("noChats")}</p>
          ) : (
            <ul className="mt-1">
              {chats.map((chat) => (
                <li key={chat.id}>
                  <button
                    type="button"
                    title={chat.title || copy("newChat")}
                    onClick={() => {
                      onSelectChat(chat.id)
                      onMenu(false)
                    }}
                    aria-current={view === "chat" && chat.id === activeChatId ? "true" : undefined}
                    className={`flex min-h-11 w-full min-w-0 items-center px-2 text-left text-sm hover:bg-elevated ${
                      view === "chat" && chat.id === activeChatId ? "bg-mint font-medium text-seal" : ""
                    } ${collapsed ? "lg:hidden" : ""}`}
                  >
                    <span className="min-w-0 truncate">{chat.title || copy("newChat")}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button
            type="button"
            title={copy("clearHistory")}
            aria-label={copy("clearHistory")}
            onClick={() => setConfirmClear(true)}
            className={`mt-1 flex min-h-11 w-full items-center gap-2 px-2 text-left text-sm text-sidebar-muted hover:bg-elevated ${
              collapsed ? "lg:justify-center" : ""
            }`}
          >
            <span className={collapsed ? "lg:hidden" : ""}>{copy("clearHistory")}</span>
            <span className={collapsed ? "hidden lg:inline-flex" : "hidden"}>
              <Icon name="clear" />
            </span>
          </button>
          <div className="mt-4">
            <p className={`px-2 text-xs text-sidebar-muted ${collapsed ? "lg:sr-only" : ""}`}>{copy("groupTax")}</p>
            <ul className="mt-1 pb-3">
              {TOOLS.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    title={copy(item.label)}
                    aria-current={view === item.id ? "page" : undefined}
                    onClick={() => choose(item.id)}
                    className={`flex min-h-11 w-full items-center gap-2 px-2 text-left text-sm hover:bg-elevated ${
                      view === item.id ? "bg-mint font-medium text-seal" : ""
                    } ${collapsed ? "lg:justify-center" : ""}`}
                  >
                    <Icon name={item.icon} />
                    <span className={`truncate ${collapsed ? "lg:sr-only" : ""}`}>{copy(item.label)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          </div>
          <div className="mt-4 pb-3">
            <button
              type="button"
              title={copy("navPrivacy")}
              aria-current={view === "privacy" ? "page" : undefined}
              onClick={() => choose("privacy")}
              className={`flex min-h-11 w-full items-center gap-2 px-2 text-left text-sm hover:bg-elevated ${
                view === "privacy" ? "bg-mint font-medium text-seal" : ""
              } ${collapsed ? "lg:justify-center" : ""}`}
            >
              <Icon name="privacy" />
              <span className={`truncate ${collapsed ? "lg:sr-only" : ""}`}>{copy("navPrivacy")}</span>
            </button>
            <p className={`mt-1 flex min-h-11 items-center gap-2 px-2 text-xs text-sidebar-muted ${collapsed ? "lg:justify-center" : ""}`}>
              <span
                aria-hidden="true"
                className={`inline-block h-2 w-2 rounded-full ${
                  service === "online" ? "bg-seal" : service === "checking" ? "bg-sidebar-muted" : "bg-warning"
                }`}
              />
              <span className={collapsed ? "lg:sr-only" : ""}>
                {service === "online"
                  ? copy("serviceOnline")
                  : service === "offline"
                    ? copy("serviceUnreachable")
                    : service === "degraded"
                      ? copy("serviceDegraded")
                      : copy("serviceChecking")}
              </span>
            </p>
          </div>
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-rule px-2 py-2 lg:px-4">
          <button
            type="button"
            aria-expanded={menuOpen}
            aria-controls={sidebarId}
            aria-label={menuOpen ? copy("closeMenu") : copy("openMenu")}
            title={menuOpen ? copy("closeMenu") : copy("openMenu")}
            onClick={() => onMenu(!menuOpen)}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center hover:bg-elevated lg:hidden"
          >
            <Icon name="menu" />
          </button>
          <button
            type="button"
            aria-expanded={!collapsed}
            aria-controls={sidebarId}
            aria-label={collapsed ? copy("expandSidebar") : copy("collapseSidebar")}
            title={collapsed ? copy("expandSidebar") : copy("collapseSidebar")}
            onClick={() => setCollapsed((current) => !current)}
            className="hidden h-11 w-11 shrink-0 items-center justify-center hover:bg-elevated lg:inline-flex"
          >
            <Icon name={collapsed ? "panelRight" : "panelLeft"} />
          </button>
          <p className="min-w-0 flex-1 truncate text-sm font-medium">{title}</p>
          <p className="hidden max-w-56 truncate text-xs text-muted xl:block">{copy("disclaimerShort")}</p>
          <HeaderMenu
            label={copy("languageLabel")}
            trigger={<span>{language === "en" ? "EN" : "UR"}</span>}
            options={[
              { id: "en", label: copy("english"), selected: language === "en", onSelect: () => onLanguage("en") },
              {
                id: "roman_urdu",
                label: copy("romanUrdu"),
                selected: language === "roman_urdu",
                onSelect: () => onLanguage("roman_urdu"),
              },
            ]}
          />
          <HeaderMenu
            label={copy("themeLabel")}
            trigger={
              <>
                <Icon name={theme === "dark" ? "moon" : "sun"} />
                <span className="hidden sm:inline">{theme === "dark" ? copy("themeDark") : copy("themeLight")}</span>
              </>
            }
            options={[
              { id: "light", label: copy("themeLight"), selected: theme === "light", onSelect: () => pickTheme("light") },
              { id: "dark", label: copy("themeDark"), selected: theme === "dark", onSelect: () => pickTheme("dark") },
            ]}
          />
        </header>
        <p className="border-b border-rule px-4 py-2 text-xs text-muted lg:hidden">{copy("disclaimerShort")}</p>
        <main id="main" tabIndex={-1} className="flex min-h-0 flex-1 flex-col outline-none">
          {children}
        </main>
        {confirmClear ? (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/45 p-4 sm:items-center">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="clear-history-title"
              className="w-full max-w-sm border border-rule bg-field p-4"
            >
              <h2 id="clear-history-title" className="text-base font-medium">
                {copy("clearConfirm")}
              </h2>
              <div className="mt-4 flex justify-end gap-2">
                <button
                  ref={cancelClearRef}
                  type="button"
                  onClick={() => setConfirmClear(false)}
                  className="min-h-11 border border-rule px-3 text-sm"
                >
                  {copy("clearCancel")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setConfirmClear(false)
                    onClearHistory()
                  }}
                  className="min-h-11 bg-low px-3 text-sm font-medium text-field"
                >
                  {copy("clearHistory")}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
