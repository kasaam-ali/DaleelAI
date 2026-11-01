/** Sidebar, top bar, and the frame around every page (SPEC §4). */

import { useEffect, useId, useRef, useState, type ReactNode } from "react"
import type { ChatSummary } from "../api/chat"
import ChatSearchPalette from "../features/chat/ChatSearchPalette"
import type { CopyKey } from "../i18n"
import type { AppView } from "../lib/hashRoute"
import { readRail, writeRail, type ClientTaxYear, type Profile, type Theme, type UiLanguage } from "../lib/session"
import Icon from "./icons"
import AppFooter from "./AppFooter"
import Brand from "./Brand"
import ChatSidebar from "./ChatSidebar"
import FilingRow from "./FilingRow"
import { TITLES, TOOLS, type ToolId } from "./nav"
import { statusText, type Service } from "./navEvents"
import StatusRow from "./StatusRow"
import ToolsNav from "./ToolsNav"
import { useModal } from "./useModal"
import { readDiscHidden, useKeyboardInset, writeDiscHidden } from "./mobile"
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
  service: Service
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
  const sidebarRef = useRef<HTMLElement>(null)
  const [rail, setRail] = useState(() => readRail(localStorage))
  const [searchOpen, setSearchOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const chatTitle = activeChatId ? chats.find((chat) => chat.id === activeChatId)?.title || copy("newChat") : copy("newChat")
  const title = view === "chat" ? chatTitle : copy(TITLES[view] ?? "navHome")

  useModal(menuOpen, sidebarRef, () => onMenu(false))
  const [discShown, setDiscShown] = useState(() => !readDiscHidden())

  function hideDisc() {
    writeDiscHidden()
    setDiscShown(false)
    setNotice(copy("discHidden"))
  }

  useKeyboardInset()

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

  function tool(id: ToolId) {
    choose(TOOLS.find((item) => item.id === id)?.view ?? "home")
  }

  const status = statusText(service, copy)
  const chatRoute = view === "chat"

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
        aria-label={chatRoute ? copy("chatsNav") : copy("navTools")}
        data-rail={rail ? "true" : "false"}
        className={`dsb sidebar-scroll fixed inset-y-0 left-0 z-40 w-[272px] overflow-y-auto transition-[transform,width] duration-200 ease-out lg:static lg:translate-x-0 ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        } ${rail ? "rail" : ""} ${chatRoute ? "sb-chat" : "sb-tools"}`}
      >
        <Brand
          copy={copy}
          homeLink={chatRoute}
          sidebarId={sidebarId}
          rail={rail}
          onHome={() => choose("home")}
          onCollapse={() => setRail(true)}
        />
        {chatRoute ? (
          <ChatSidebar
            chats={chats}
            activeChatId={activeChatId}
            copy={copy}
            onTool={tool}
            onNewChat={() => {
              onNewChat()
              onMenu(false)
            }}
            onSearch={() => setSearchOpen(true)}
            onSelectChat={(chatId) => {
              onSelectChat(chatId)
              onMenu(false)
            }}
            onRename={onRename}
            onDelete={onDelete}
            onToast={setNotice}
          />
        ) : (
          <ToolsNav view={view} copy={copy} onTool={tool} />
        )}
        <div className="grow" />
        <FilingRow
          profile={profile}
          taxYear={taxYear}
          taxYearSet={taxYearSet}
          filingSaved={filingSaved}
          copy={copy}
          onProfile={onProfile}
          onTaxYear={onTaxYear}
          onClearFiling={onClearFiling}
        />
        {/* TODO(PR 8): StatusRow opens About & settings at sec=status once that section lands. */}
        <StatusRow service={service} copy={copy} onOpen={() => choose("privacy")} />
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
            className="iconbtn theme-toggle"
            aria-label={copy("themeToggle")}
            title={copy("themeToggle")}
            aria-pressed={theme === "dark"}
            onClick={onTheme}
          >
            <Icon name="sun" />
          </button>
        </header>
        {discShown ? (
          <div className="m-disc" data-mobile-disclaimer>
            <span>{copy("disclaimerShort")}</span>
            <button type="button" className="iconbtn" aria-label={copy("closeLabel")} title={copy("closeLabel")} onClick={hideDisc}>
              <Icon name="close" size="sm" />
            </button>
          </div>
        ) : null}
        {service === "offline" || service === "degraded" ? (
          <p className="flex items-center gap-2 border-b border-rule px-4 py-2 text-xs text-muted lg:hidden" role="status">
            <span aria-hidden="true" className="inline-block h-2 w-2 shrink-0 rounded-full bg-warning" />
            {status}
          </p>
        ) : null}
        <main id="main" tabIndex={-1} className="flex min-h-0 flex-1 flex-col outline-none">
          {children}
        </main>
        <AppFooter variant="site" copy={copy} />
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
