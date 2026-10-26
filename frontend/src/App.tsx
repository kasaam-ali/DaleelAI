/** Holds language, theme, profile, and which page is open. */

import { useEffect, useRef, useState } from "react"
import { serviceState, useBrowserOnline, useHealth } from "./api/health"
import { deleteSession } from "./api/session"
import CalculatorPage from "./features/calculator/CalculatorPage"
import ChecklistsPage from "./features/checklists/ChecklistsPage"
import ChatPage from "./features/chat/ChatPage"
import { useChatHistory } from "./features/chat/useChatHistory"
import HomePage from "./features/home/HomePage"
import EvaluationPage from "./features/evaluation/EvaluationPage"
import ExpertsPage from "./features/experts/ExpertsPage"
import FilerPage from "./features/filer/FilerPage"
import NoticePage from "./features/notice/NoticePage"
import PrivacyPage from "./features/privacy/PrivacyPage"
import UpdatesPage from "./features/updates/UpdatesPage"
import { t, type CopyKey } from "./i18n"
import { parseHash, type AppView } from "./lib/hashRoute"
import {
  THEME_KEY,
  clearStoredHistory,
  readChatId,
  readLanguage,
  readProfile,
  readOfflineQueue,
  readSessionId,
  readTaxYear,
  sanitizeProfile,
  writeChatId,
  writeLanguage,
  writeProfile,
  writeTaxYear,
  CHAT_KEY,
  type ClientTaxYear,
  type Profile,
  type Theme,
  type UiLanguage,
} from "./lib/session"
import AppShell from "./shell/AppShell"

export default function App() {
  const [language, setLanguage] = useState<UiLanguage>(() => readLanguage(localStorage))
  const [profile, setProfile] = useState<Profile>(() => readProfile(localStorage))
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  )
  const routed = parseHash(window.location.hash)
  // Queued offline questions flush on load; show them in the chat instead of leaving the user on Home.
  const [view, setView] = useState<AppView>(() =>
    routed.view === "home" && readOfflineQueue(localStorage).length > 0 ? "chat" : routed.view,
  )
  const [taxYear, setTaxYear] = useState<ClientTaxYear>(() => readTaxYear(localStorage))
  const [launch, setLaunch] = useState<{ id: string; text: string } | null>(null)
  const [historyKey, setHistoryKey] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)
  const [sessionId, setSessionId] = useState(() => readSessionId(localStorage))
  const [clearError, setClearError] = useState<string | null>(null)
  const [chatId, setChatId] = useState<string | null>(() => routed.chatId ?? readChatId(localStorage))
  const [expertQuery, setExpertQuery] = useState("")
  const [expertCategory, setExpertCategory] = useState<string | null>(null)
  const [checklistTemplate, setChecklistTemplate] = useState("")
  const copy = (key: CopyKey) => t(language, key)
  const online = useBrowserOnline()
  const health = useHealth()
  const history = useChatHistory(sessionId)
  const wasOnline = useRef(online)
  const refetchHealth = health.refetch
  useEffect(() => {
    if (online && !wasOnline.current) void refetchHealth()
    wasOnline.current = online
  }, [online, refetchHealth])

  function changeLanguage(next: UiLanguage) {
    setLanguage(next)
    writeLanguage(localStorage, next)
  }

  function changeProfile(patch: Partial<Profile>) {
    setProfile((current) => sanitizeProfile({ ...current, ...patch }))
  }

  useEffect(() => {
    writeProfile(localStorage, profile)
  }, [profile])

  useEffect(() => {
    document.documentElement.lang = language === "roman_urdu" ? "ur-Latn" : "en"
    document.documentElement.dir = "ltr"
  }, [language])

  function changeTaxYear(next: ClientTaxYear) {
    setTaxYear(next)
    writeTaxYear(localStorage, next)
  }

  function changeTheme() {
    const next = theme === "dark" ? "light" : "dark"
    setTheme(next)
    document.documentElement.dataset.theme = next
    localStorage.setItem(THEME_KEY, next)
  }

  useEffect(() => {
    function onPop() {
      const next = parseHash(window.location.hash)
      setView(next.view)
      if (next.chatId) {
        setChatId(next.chatId)
        writeChatId(localStorage, next.chatId)
      }
    }
    window.addEventListener("popstate", onPop)
    return () => window.removeEventListener("popstate", onPop)
  }, [])

  function go(next: AppView) {
    setView(next)
    const nextHash = next === "home" ? "" : `#/${next}`
    const current = window.location.hash
    if (next === "home") {
      if (current === "" || current === "#" || current === "#/" || current === "#/home") return
      window.history.pushState({ view: "home" }, "", `${window.location.pathname}${window.location.search}`)
      return
    }
    if (current === nextHash) return
    window.history.pushState({ view: next }, "", nextHash)
  }

  function selectChat(next: string | null) {
    setLaunch(null)
    setChatId(next)
    go("chat")
    if (next) writeChatId(localStorage, next)
    else localStorage.removeItem(CHAT_KEY)
    setHistoryKey((current) => current + 1)
  }

  function askFromHome(question: string) {
    const text = question.trim()
    if (!text) return
    setChatId(null)
    localStorage.removeItem(CHAT_KEY)
    setLaunch({ id: crypto.randomUUID(), text })
    go("chat")
  }

  async function clearHistory() {
    setClearError(null)
    try {
      const next = await clearStoredHistory(localStorage, sessionId, deleteSession)
      setSessionId(next)
      setChatId(null)
    } catch {
      setClearError(copy("clearFailed"))
    }
  }

  const service = serviceState(online, {
    error: health.isError,
    ok: health.isSuccess,
    status: health.data?.status,
  })

  return (
    <AppShell
      view={view}
      language={language}
      theme={theme}
      profile={profile}
      chats={history.chats}
      snippets={history.snippets}
      activeChatId={chatId}
      service={service}
      menuOpen={menuOpen}
      copy={copy}
      onView={go}
      onNewChat={() => selectChat(null)}
      onSelectChat={selectChat}
      onClearHistory={() => void clearHistory()}
      clearError={clearError}
      onRename={history.rename}
      onDelete={history.remove}
      onPrefetchSnippets={history.prefetchSnippets}
      onLanguage={changeLanguage}
      onTheme={changeTheme}
      onProfile={changeProfile}
      onMenu={setMenuOpen}
    >
      {view === "home" ? <HomePage copy={copy} onOpen={go} onAsk={askFromHome} /> : null}
      <div className={view === "chat" ? "contents" : "hidden"} aria-hidden={view !== "chat"}>
        <ChatPage
          language={language}
          profile={profile}
          copy={copy}
          chatId={chatId}
          sessionId={sessionId}
          launch={launch}
          historyKey={historyKey}
          taxYear={taxYear}
          onLaunchConsumed={() => setLaunch(null)}
          onChatId={(id) => {
            setChatId(id)
            writeChatId(localStorage, id)
          }}
          onActivity={() => history.refresh()}
          onProfile={changeProfile}
          onTaxYear={changeTaxYear}
          onSnippet={history.rememberSnippet}
        />
      </div>
      {view !== "home" && view !== "chat" ? (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className={`mx-auto w-full px-4 py-6 sm:px-8 ${view === "calculator" || view === "filer" ? "max-w-4xl" : "max-w-3xl"}`}>
            {view === "calculator" ? (
              <CalculatorPage
                copy={copy}
                onOpenChecklist={(templateId) => {
                  setChecklistTemplate(templateId)
                  go("checklist")
                }}
              />
            ) : null}
            {view === "filer" ? (
              <FilerPage
                copy={copy}
                onOpenChecklist={(templateId) => {
                  setChecklistTemplate(templateId)
                  go("checklist")
                }}
              />
            ) : null}
            {view === "notice" ? (
              <NoticePage
                copy={copy}
                language={language}
                onFindExpert={(category) => {
                  setExpertQuery(`${category} notice`)
                  setExpertCategory(category)
                  go("experts")
                }}
              />
            ) : null}
            {view === "checklist" ? (
              <ChecklistsPage copy={copy} language={language} preferredTemplate={checklistTemplate} />
            ) : null}
            {view === "experts" ? (
              <ExpertsPage copy={copy} initialQuery={expertQuery} initialCategory={expertCategory} />
            ) : null}
            {view === "updates" ? <UpdatesPage copy={copy} language={language} /> : null}
            {view === "evaluation" ? <EvaluationPage copy={copy} /> : null}
            {view === "privacy" ? (
              <PrivacyPage copy={copy} onClearHistory={() => void clearHistory()} clearError={clearError} />
            ) : null}
          </div>
        </div>
      ) : null}
    </AppShell>
  )
}
