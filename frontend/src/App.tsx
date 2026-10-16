import { useEffect, useState } from "react"
import { listChats, type ChatSummary } from "./api/chat"
import { useHealth } from "./api/health"
import CalculatorPage from "./features/calculator/CalculatorPage"
import ChecklistsPage from "./features/checklists/ChecklistsPage"
import ChatPage from "./features/chat/ChatPage"
import HomePage from "./features/home/HomePage"
import EvaluationPage from "./features/evaluation/EvaluationPage"
import ExpertsPage from "./features/experts/ExpertsPage"
import FilerPage from "./features/filer/FilerPage"
import NoticePage from "./features/notice/NoticePage"
import PrivacyPage from "./features/privacy/PrivacyPage"
import UpdatesPage from "./features/updates/UpdatesPage"
import { t, type CopyKey } from "./i18n"
import {
  THEME_KEY,
  clearLocalHistory,
  readChatId,
  readLanguage,
  readProfile,
  readSessionId,
  sanitizeProfile,
  writeChatId,
  writeLanguage,
  writeProfile,
  CHAT_KEY,
  type Profile,
  type Theme,
  type UiLanguage,
} from "./lib/session"
import AppShell, { type AppView } from "./shell/AppShell"

const VIEWS: AppView[] = [
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
]

function viewFromHash(): AppView {
  const name = window.location.hash.replace(/^#\/?/, "")
  return VIEWS.includes(name as AppView) ? (name as AppView) : "home"
}

export default function App() {
  const [language, setLanguage] = useState<UiLanguage>(() => readLanguage(localStorage))
  const [profile, setProfile] = useState<Profile>(() => readProfile(localStorage))
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  )
  const [view, setView] = useState<AppView>(() => viewFromHash())
  const [launch, setLaunch] = useState<{ id: string; text: string } | null>(null)
  const [historyKey, setHistoryKey] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)
  const [sessionId, setSessionId] = useState(() => readSessionId(localStorage))
  const [chatId, setChatId] = useState<string | null>(() => readChatId(localStorage))
  const [chats, setChats] = useState<ChatSummary[]>([])
  const [revision, setRevision] = useState(0)
  const [expertQuery, setExpertQuery] = useState("")
  const [expertCategory, setExpertCategory] = useState<string | null>(null)
  const [checklistTemplate, setChecklistTemplate] = useState("")
  const copy = (key: CopyKey) => t(language, key)
  const health = useHealth()

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
    let cancelled = false
    listChats(sessionId)
      .then((rows) => {
        if (!cancelled) setChats(rows)
      })
      .catch(() => {
        if (!cancelled) setChats([])
      })
    return () => {
      cancelled = true
    }
  }, [sessionId, revision])

  function changeTheme() {
    const next = theme === "dark" ? "light" : "dark"
    setTheme(next)
    document.documentElement.dataset.theme = next
    localStorage.setItem(THEME_KEY, next)
  }

  useEffect(() => {
    function onPop() {
      setView(viewFromHash())
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

  function clearHistory() {
    const next = clearLocalHistory(localStorage)
    setSessionId(next)
    setChatId(null)
    setChats([])
    setRevision((current) => current + 1)
  }

  const service = health.isPending ? "checking" : health.isError ? "degraded" : "online"

  return (
    <AppShell
      view={view}
      language={language}
      theme={theme}
      profile={profile}
      chats={chats}
      activeChatId={chatId}
      service={service}
      menuOpen={menuOpen}
      copy={copy}
      onView={go}
      onNewChat={() => selectChat(null)}
      onSelectChat={selectChat}
      onClearHistory={clearHistory}
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
          onLaunchConsumed={() => setLaunch(null)}
          onChatId={(id) => {
            setChatId(id)
            writeChatId(localStorage, id)
          }}
          onActivity={() => setRevision((current) => current + 1)}
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
            {view === "updates" ? <UpdatesPage copy={copy} /> : null}
            {view === "evaluation" ? <EvaluationPage copy={copy} /> : null}
            {view === "privacy" ? <PrivacyPage copy={copy} onClearHistory={clearHistory} /> : null}
          </div>
        </div>
      ) : null}
    </AppShell>
  )
}
