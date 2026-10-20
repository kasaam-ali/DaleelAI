/** Sidebar, top bar, and the frame around every page (SPEC §4). */

import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react"
import type { ChatSummary } from "../api/chat"
import ChatSearchPalette from "../features/chat/ChatSearchPalette"
import HistoryList from "../features/chat/HistoryList"
import type { CopyKey } from "../i18n"
import { FilingPopover } from "../features/onboarding/ProfilePanel"
import type { AppView } from "../lib/hashRoute"
import { readRail, writeRail, type ClientTaxYear, type Profile, type Theme, type UiLanguage } from "../lib/session"
import Icon from "./icons"
import { NAV, TITLES, filingSummary } from "./nav"
import { useModal } from "./useModal"
import "./shell.css"

export type { AppView }

type Copy = (key: CopyKey) => string

export default function AppShell({
  view,
  language,
  theme,
  profile,
  taxYear,
  taxYearSet,
  filingSaved,
  chats,
  snippets,
  activeChatId,
  service,
  menuOpen,
  copy,
  onView,
  onNewChat,
  onSelectChat,
  onRename,
  onDelete,
  onPrefetchSnippets,
  onLanguage,
  onTheme,
  onProfile,
  onTaxYear,
  onClearFiling,
  onMenu,
  children,
}: {
  view: AppView
  language: UiLanguage
  theme: Theme
  profile: Profile
  taxYear: ClientTaxYear
  taxYearSet: boolean
  filingSaved: boolean
  chats: ChatSummary[]
  snippets: Record<string, string>
  activeChatId: string | null
  service: "checking" | "online" | "degraded" | "offline"
  menuOpen: boolean
  copy: Copy
  onView: (view: AppView) => void
  onNewChat: () => void
  onSelectChat: (chatId: string) => void
  onRename: (chatId: string, title: string) => Promise<void>
  onDelete: (chatId: string) => Promise<void>
  onPrefetchSnippets: () => void
  onLanguage: (language: UiLanguage) => void
  onTheme: () => void
  onProfile: (patch: Partial<Profile>) => void
  onTaxYear: (taxYear: ClientTaxYear) => void
  onClearFiling: () => void
  onMenu: (open: boolean) => void
  children: ReactNode
}) {
  const sidebarId = useId()
  const popoverId = useId()
  const sidebarRef = useRef<HTMLElement>(null)
  const [rail, setRail] = useState(() => readRail(localStorage))
  const [searchOpen, setSearchOpen] = useState(false)
  const [filingOpen, setFilingOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const chatTitle = activeChatId ? chats.find((chat) => chat.id === activeChatId)?.title || copy("newChat") : copy("newChat")
  const title = view === "chat" ? chatTitle : copy(TITLES[view] ?? "navHome")
  const closeFiling = useCallback(() => setFilingOpen(false), [])

  useModal(menuOpen, sidebarRef, () => onMenu(false))

  useEffect(() => {
    writeRail(localStorage, rail)
  }, [rail])

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setSearchOpen((open) => !open)
      }
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [])

  useEffect(() => {
    if (searchOpen) onPrefetchSnippets()
  }, [searchOpen, onPrefetchSnippets])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), 2600)
    return () => window.clearTimeout(timer)
  }, [notice])

  function choose(next: AppView) {
    if (next === "chat") onNewChat()
    else onView(next)
    onMenu(false)
  }

  function navItem(item: (typeof NAV)[number]) {
    // Sawal poocho opens a new chat; inside a chat the recents row is the current page, so only the rail marks it.
    const on = view === item.id && item.id !== "chat"
    const onRail = item.id === "chat" && view === "chat"
    return (
      <button
        key={item.id}
        type="button"
        title={copy(item.label)}
        aria-current={on ? "page" : undefined}
        onClick={() => choose(item.id)}
        className={`nav-item keep${on ? " on" : ""}${onRail ? " on-rail" : ""}`}
      >
        <Icon name={item.icon} />
        <span className="lbl">{copy(item.label)}</span>
        <span className="short" aria-hidden="true">
          {copy(item.short)}
        </span>
      </button>
    )
  }

  const statusText =
    service === "online"
      ? copy("serviceOnline")
      : service === "offline"
        ? copy("serviceUnreachable")
        : service === "degraded"
          ? copy("serviceDegraded")
          : copy("serviceChecking")

  return (
    <div className="flex h-dvh bg-paper text-ink" data-drawer={menuOpen ? "open" : "closed"}>
      <a href="#main" className="skip-link">
        {copy("skipToQuestion")}
      </a>
      {menuOpen ? (
        <button
          type="button"
          aria-label={copy("closeMenu")}
          data-modal-scrim
          className="fixed inset-0 z-30 bg-ink/40 lg:hidden"
          onClick={() => onMenu(false)}
        />
      ) : null}
      <aside
        id={sidebarId}
        ref={sidebarRef}
        aria-label={copy("product")}
        data-rail={rail ? "true" : "false"}
        className={`dsb sidebar-scroll fixed inset-y-0 left-0 z-40 w-[272px] overflow-y-auto transition-[transform,width] duration-200 ease-out lg:static lg:translate-x-0 ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        } ${rail ? "rail" : ""}`}
      >
        <div className="brand">
          <span className="mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 5.5h7.2L17 9.2V18.5H6v-13z" />
              <path d="M13 5.5V9h4" />
            </svg>
          </span>
          <span className="lbl">
            <b>DaleelAI</b>
            <small>{copy("subtitle")}</small>
          </span>
          <button
            type="button"
            className="iconbtn sb-collapse only-desk"
            aria-label={copy("collapseSidebar")}
            title={copy("collapseSidebar")}
            aria-expanded={!rail}
            aria-controls={sidebarId}
            onClick={() => setRail(true)}
          >
            <Icon name="panelLeft" />
          </button>
        </div>
        <button
          type="button"
          data-new-chat
          title={copy("newChat")}
          className="newchat"
          onClick={() => {
            onNewChat()
            onMenu(false)
          }}
        >
          <Icon name="plus" />
          <span className="lbl">{copy("newChat")}</span>
        </button>
        <button type="button" data-search-chats title={copy("searchChats")} className="searchbox" onClick={() => setSearchOpen(true)}>
          <Icon name="search" size="sm" />
          <span className="lbl">{copy("searchChats")}</span>
          <kbd className="lbl">Ctrl K</kbd>
        </button>
        <nav aria-label={copy("navTools")} className="contents">
          {navItem(NAV[0])}
          <p className="nav-label">{copy("navTools")}</p>
          {NAV.filter((item) => item.group === "tools").map(navItem)}
        </nav>
        <div className="recents">
          <HistoryList
            chats={chats}
            activeId={view === "chat" ? activeChatId : null}
            copy={copy}
            heading={copy("recentsLabel")}
            onSelect={(chatId) => {
              onSelectChat(chatId)
              onMenu(false)
            }}
            onRename={onRename}
            onDelete={onDelete}
            onOpenNew={() => {
              onNewChat()
              onMenu(false)
            }}
            onToast={setNotice}
          />
        </div>
        <div className="grow" />
        {/* TODO(PR 8): when About & settings lands, this link opens it at sec=how with the sticky sub-nav from SPEC §5.6. */}
        <button
          type="button"
          title={copy("navAbout")}
          aria-current={view === "privacy" ? "page" : undefined}
          onClick={() => choose("privacy")}
          className={`nav-item keep${view === "privacy" ? " on" : ""}`}
        >
          <Icon name="gear" />
          <span className="lbl">{copy("navAbout")}</span>
          <span className="short" aria-hidden="true">
            {copy("railAbout")}
          </span>
        </button>
        <div className={`filing${filingOpen ? " open" : ""}`}>
          {filingOpen ? (
            <FilingPopover
              id={popoverId}
              profile={profile}
              taxYear={taxYear}
              taxYearSet={taxYearSet}
              copy={copy}
              onChange={onProfile}
              onTaxYear={onTaxYear}
              onClear={onClearFiling}
              onClose={closeFiling}
            />
          ) : null}
          <button
            type="button"
            data-filing-row
            className="filing-row"
            title={copy("profileTitle")}
            aria-expanded={filingOpen}
            aria-controls={filingOpen ? popoverId : undefined}
            aria-haspopup="dialog"
            onClick={() => setFilingOpen((open) => !open)}
          >
            <span className="av">
              <Icon name="user" size="sm" />
            </span>
            <span className="lbl fr-t">
              <b>{copy("profileTitle")}</b>
              <small data-filing-summary>{filingSummary(profile, taxYear, taxYearSet, filingSaved, copy)}</small>
            </span>
            <Icon name="chev" size="sm" className="lbl updown" />
          </button>
        </div>
        <p className="status" role="status" title={statusText}>
          <span
            aria-hidden="true"
            className={`dot ${service === "online" ? "bg-seal" : service === "checking" ? "bg-sidebar-muted" : "bg-warning"}`}
          />
          <span className="lbl">{statusText}</span>
        </p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="dtop">
          <button
            type="button"
            aria-expanded={menuOpen}
            aria-controls={sidebarId}
            aria-label={menuOpen ? copy("closeMenu") : copy("openMenu")}
            title={menuOpen ? copy("closeMenu") : copy("openMenu")}
            onClick={() => onMenu(!menuOpen)}
            className="iconbtn only-mobile"
          >
            <Icon name="menu" />
          </button>
          {rail ? (
            <button
              type="button"
              aria-expanded={false}
              aria-controls={sidebarId}
              aria-label={copy("expandSidebar")}
              title={copy("expandSidebar")}
              onClick={() => setRail(false)}
              className="iconbtn only-desk"
            >
              <Icon name="panelLeft" />
            </button>
          ) : null}
          <p className="title">{title}</p>
          <button
            type="button"
            className="pill-btn"
            lang={language === "en" ? "ur-Latn" : "en"}
            onClick={() => onLanguage(language === "en" ? "roman_urdu" : "en")}
          >
            {copy("langSwitch")}
          </button>
          <button
            type="button"
            className="iconbtn"
            aria-label={copy("themeToggle")}
            title={copy("themeToggle")}
            aria-pressed={theme === "dark"}
            onClick={onTheme}
          >
            <Icon name="sun" />
          </button>
        </header>
        {service === "offline" || service === "degraded" ? (
          <p className="flex items-center gap-2 border-b border-rule px-4 py-2 text-xs text-muted lg:hidden" role="status">
            <span aria-hidden="true" className="inline-block h-2 w-2 shrink-0 rounded-full bg-warning" />
            {statusText}
          </p>
        ) : null}
        <main id="main" tabIndex={-1} className="flex min-h-0 flex-1 flex-col outline-none">
          {children}
        </main>
      </div>
      {searchOpen ? (
        <ChatSearchPalette
          chats={chats}
          snippets={snippets}
          copy={copy}
          onOpen={(chatId) => {
            setSearchOpen(false)
            onSelectChat(chatId)
            onMenu(false)
          }}
          onClose={() => {
            setSearchOpen(false)
            document.querySelector<HTMLElement>("[data-search-chats]")?.focus()
          }}
        />
      ) : null}
      {notice ? (
        <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex justify-center">
          <p role="status" data-motion="rise" className="motion-rise rounded-full border border-rule bg-field px-4 py-2 text-sm shadow-[var(--shadow)]">
            {notice}
          </p>
        </div>
      ) : null}
    </div>
  )
}
