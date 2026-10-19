import { useEffect, useState } from "react"
import { useHealth } from "./api/health"
import CalculatorPage from "./features/calculator/CalculatorPage"
import ChecklistsPage from "./features/checklists/ChecklistsPage"
import ChatPage from "./features/chat/ChatPage"
import EvaluationPage from "./features/evaluation/EvaluationPage"
import ExpertsPage from "./features/experts/ExpertsPage"
import FilerPage from "./features/filer/FilerPage"
import NoticePage from "./features/notice/NoticePage"
import PrivacyPage from "./features/privacy/PrivacyPage"
import ProfilePanel from "./features/onboarding/ProfilePanel"
import UpdatesPage from "./features/updates/UpdatesPage"
import { t, type CopyKey } from "./i18n"
import {
  THEME_KEY,
  readLanguage,
  readProfile,
  sanitizeProfile,
  writeLanguage,
  writeProfile,
  type Profile,
  type Theme,
  type UiLanguage,
} from "./lib/session"

type View =
  | "chat"
  | "calculator"
  | "filer"
  | "notice"
  | "checklist"
  | "experts"
  | "evaluation"
  | "updates"
  | "privacy"

const NAV: { id: View; label: CopyKey }[] = [
  { id: "chat", label: "navChat" },
  { id: "calculator", label: "navCalculator" },
  { id: "filer", label: "navFiler" },
  { id: "notice", label: "navNotice" },
  { id: "checklist", label: "navChecklist" },
  { id: "experts", label: "navExperts" },
  { id: "updates", label: "navUpdates" },
  { id: "evaluation", label: "navEvaluation" },
  { id: "privacy", label: "navPrivacy" },
]

export default function App() {
  const [language, setLanguage] = useState<UiLanguage>(() => readLanguage(localStorage))
  const [profile, setProfile] = useState<Profile>(() => readProfile(localStorage))
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  )
  const [view, setView] = useState<View>("chat")
  const [menuOpen, setMenuOpen] = useState(false)
  const [expertQuery, setExpertQuery] = useState("")
  const [expertCategory, setExpertCategory] = useState<string | null>(null)
  const [checklistTemplate, setChecklistTemplate] = useState("")
  const copy = (key: CopyKey) => t(language, key)
  const pageTitle = copy(NAV.find((item) => item.id === view)?.label ?? "navChat")

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
    document.documentElement.lang = language === "roman_urdu" ? "ur" : "en"
  }, [language])

  useEffect(() => {
    if (!menuOpen) return
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [menuOpen])

  function changeTheme() {
    const next = theme === "dark" ? "light" : "dark"
    setTheme(next)
    document.documentElement.dataset.theme = next
    localStorage.setItem(THEME_KEY, next)
  }

  function openView(next: View) {
    setView(next)
    setMenuOpen(false)
  }

  return (
    <div className="min-h-dvh bg-paper font-civic text-ink md:grid md:h-dvh md:grid-cols-[272px_minmax(0,1fr)] md:overflow-hidden">
      <a
        href="#ask"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded-lg focus:bg-field focus:px-3 focus:py-2"
      >
        {copy("skipToQuestion")}
      </a>
      {menuOpen ? (
        <button
          type="button"
          className="no-print fixed inset-0 z-30 bg-ink/40 md:hidden"
          aria-label={copy("closeMenu")}
          onClick={() => setMenuOpen(false)}
        />
      ) : null}
      <aside
        id="app-nav"
        className={`no-print ${
          menuOpen ? "fixed inset-y-0 left-0 z-40 flex w-[min(20rem,88vw)]" : "hidden"
        } flex-col bg-sidebar text-sidebar-ink md:static md:flex md:h-dvh md:w-auto md:overflow-y-auto`}
      >
        <div className="flex items-center gap-3 px-5 pt-6 pb-4">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-gold/20 font-statute text-xl text-gold">
            D
          </span>
          <div>
            <p className="font-statute text-2xl leading-none tracking-tight">{copy("product")}</p>
            <p className="mt-1 text-xs tracking-wide text-sidebar-muted">FBR · SECP</p>
          </div>
        </div>
        <nav aria-label={copy("navLabel")} className="grid gap-1 px-3">
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-current={view === item.id ? "page" : undefined}
              onClick={() => openView(item.id)}
              className={`min-h-11 rounded-xl px-3 text-left text-sm transition ${
                view === item.id
                  ? "bg-sidebar-ink font-semibold text-sidebar"
                  : "text-sidebar-muted hover:bg-white/5 hover:text-sidebar-ink"
              }`}
            >
              {copy(item.label)}
            </button>
          ))}
        </nav>
        <div className="mt-auto border-t border-white/10 px-4 py-4">
          <div className="mb-4 flex flex-wrap gap-2">
            <span className="sr-only">{copy("languageLabel")}</span>
            <button
              type="button"
              aria-pressed={language === "en"}
              onClick={() => changeLanguage("en")}
              className={`min-h-11 rounded-full px-3 text-sm ${
                language === "en" ? "bg-sidebar-ink text-sidebar" : "border border-white/20 text-sidebar-ink"
              }`}
            >
              {copy("english")}
            </button>
            <button
              type="button"
              aria-pressed={language === "roman_urdu"}
              onClick={() => changeLanguage("roman_urdu")}
              className={`min-h-11 rounded-full px-3 text-sm ${
                language === "roman_urdu"
                  ? "bg-sidebar-ink text-sidebar"
                  : "border border-white/20 text-sidebar-ink"
              }`}
            >
              {copy("romanUrdu")}
            </button>
          </div>
          <ProfilePanel profile={profile} copy={copy} onChange={changeProfile} compact />
        </div>
      </aside>
      <div className="flex min-h-dvh min-w-0 flex-col md:h-dvh">
        <header className="no-print sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-rule bg-paper/90 px-4 py-3 backdrop-blur sm:px-6">
          <button
            type="button"
            className="inline-flex min-h-11 items-center rounded-xl border border-rule px-3 text-sm md:hidden"
            aria-expanded={menuOpen}
            aria-controls="app-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? copy("closeMenu") : copy("menu")}
          </button>
          <div className="min-w-0 flex-1">
            <p className="truncate font-statute text-xl leading-none">{pageTitle}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="sr-only">{copy("languageLabel")}</span>
            <button
              type="button"
              aria-pressed={language === "en"}
              onClick={() => changeLanguage("en")}
              className={`min-h-11 rounded-full px-3 text-sm md:hidden ${
                language === "en" ? "bg-ink text-paper" : "border border-rule"
              }`}
            >
              {copy("english")}
            </button>
            <button
              type="button"
              aria-pressed={language === "roman_urdu"}
              onClick={() => changeLanguage("roman_urdu")}
              className={`min-h-11 rounded-full px-3 text-sm md:hidden ${
                language === "roman_urdu" ? "bg-ink text-paper" : "border border-rule"
              }`}
            >
              {copy("romanUrdu")}
            </button>
            <button
              type="button"
              onClick={changeTheme}
              className="min-h-11 rounded-full border border-rule px-3 text-sm"
            >
              {theme === "dark" ? copy("themeToLight") : copy("themeToDark")}
            </button>
            <ServiceStatus copy={copy} />
          </div>
        </header>
        <main
          className={
            view === "chat" ? "min-h-0 flex-1 overflow-hidden" : "min-h-0 flex-1 overflow-y-auto"
          }
        >
          <div className={view === "chat" ? "h-full" : "hidden"}>
            <ChatPage language={language} profile={profile} copy={copy} />
          </div>
          {view === "chat" ? null : (
            <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
              {view === "calculator" ? (
                <CalculatorPage
                  copy={copy}
                  onOpenChecklist={(templateId) => {
                    setChecklistTemplate(templateId)
                    setView("checklist")
                  }}
                />
              ) : null}
              {view === "filer" ? (
                <FilerPage
                  copy={copy}
                  onOpenChecklist={(templateId) => {
                    setChecklistTemplate(templateId)
                    setView("checklist")
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
                    setView("experts")
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
              {view === "privacy" ? <PrivacyPage copy={copy} /> : null}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

function ServiceStatus({ copy }: { copy: (key: CopyKey) => string }) {
  const health = useHealth()
  const state = health.isPending ? "checking" : health.isError ? "down" : "up"
  const text =
    state === "checking"
      ? copy("serviceChecking")
      : state === "down"
        ? copy("serviceUnreachable")
        : copy("serviceReachable")
  return (
    <p className="hidden items-center gap-2 text-sm text-muted lg:flex" role="status">
      <span
        className={`h-2 w-2 rounded-full ${
          state === "up" ? "bg-seal" : state === "down" ? "bg-low" : "bg-gold"
        }`}
        aria-hidden="true"
      />
      {text}
    </p>
  )
}
