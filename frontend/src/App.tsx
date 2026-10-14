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

export default function App() {
  const [language, setLanguage] = useState<UiLanguage>(() => readLanguage(localStorage))
  const [profile, setProfile] = useState<Profile>(() => readProfile(localStorage))
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  )
  const [view, setView] = useState<
    "chat" | "calculator" | "filer" | "notice" | "checklist" | "experts" | "evaluation" | "updates" | "privacy"
  >("chat")
  const [expertQuery, setExpertQuery] = useState("")
  const [expertCategory, setExpertCategory] = useState<string | null>(null)
  const [checklistTemplate, setChecklistTemplate] = useState("")
  const copy = (key: CopyKey) => t(language, key)

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

  function changeTheme() {
    const next = theme === "dark" ? "light" : "dark"
    setTheme(next)
    document.documentElement.dataset.theme = next
    localStorage.setItem(THEME_KEY, next)
  }

  return (
    <div className="min-h-dvh bg-paper font-civic text-ink">
      <a
        href="#ask"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-10 focus:bg-field focus:px-3 focus:py-2"
      >
        {copy("skipToQuestion")}
      </a>
      <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
        <header>
          <h1 className="font-statute text-5xl leading-none">{copy("product")}</h1>
          <p className="mt-3 max-w-[36ch] text-lg leading-7">{copy("lede")}</p>
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <span className="sr-only">{copy("languageLabel")}</span>
            <button
              type="button"
              aria-pressed={language === "en"}
              onClick={() => changeLanguage("en")}
              className={`min-h-11 px-3 text-sm ${language === "en" ? "bg-ink text-paper" : "border border-rule"}`}
            >
              {copy("english")}
            </button>
            <button
              type="button"
              aria-pressed={language === "roman_urdu"}
              onClick={() => changeLanguage("roman_urdu")}
              className={`min-h-11 px-3 text-sm ${language === "roman_urdu" ? "bg-ink text-paper" : "border border-rule"}`}
            >
              {copy("romanUrdu")}
            </button>
            <button type="button" onClick={changeTheme} className="min-h-11 border border-rule px-3 text-sm">
              {theme === "dark" ? copy("themeToLight") : copy("themeToDark")}
            </button>
            {(
              [
                ["chat", "navChat"],
                ["calculator", "navCalculator"],
                ["filer", "navFiler"],
                ["notice", "navNotice"],
                ["checklist", "navChecklist"],
                ["experts", "navExperts"],
                ["updates", "navUpdates"],
                ["evaluation", "navEvaluation"],
                ["privacy", "navPrivacy"],
              ] as const
            ).map(([item, label]) => (
              <button
                key={item}
                type="button"
                aria-pressed={view === item}
                onClick={() => setView(item)}
                className={`min-h-11 px-3 text-sm ${view === item ? "bg-ink text-paper" : "border border-rule"}`}
              >
                {copy(label)}
              </button>
            ))}
          </div>
          <ServiceStatus copy={copy} />
        </header>
        <ProfilePanel
          profile={profile}
          copy={copy}
          onChange={changeProfile}
        />
        <main>
          <div className={view === "chat" ? "" : "hidden"}>
            <ChatPage language={language} profile={profile} copy={copy} />
          </div>
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
        </main>
      </div>
    </div>
  )
}

function ServiceStatus({ copy }: { copy: (key: CopyKey) => string }) {
  const health = useHealth()
  const text = health.isPending
    ? copy("serviceChecking")
    : health.isError
      ? copy("serviceUnreachable")
      : copy("serviceReachable")
  return <p className="mt-4 text-sm text-muted">{text}</p>
}
