import { useEffect, useState } from "react"
import {
  checklistTemplates,
  markChecklistStep,
  startChecklist,
  type Checklist,
  type ChecklistTemplate,
} from "../../api/phase5"
import type { CopyKey } from "../../i18n"
import type { UiLanguage } from "../../lib/session"

type Copy = (key: CopyKey) => string
const STORAGE_KEY = "daleelai.checklists"
const inputClass = "mt-1 min-h-11 w-full border border-rule bg-field px-3 text-base text-ink"

export default function ChecklistsPage({
  copy,
  language,
  preferredTemplate = "",
}: {
  copy: Copy
  language: UiLanguage
  preferredTemplate?: string
}) {
  const [templates, setTemplates] = useState<ChecklistTemplate[]>([])
  const [templateId, setTemplateId] = useState(preferredTemplate)
  const [appliedTemplate, setAppliedTemplate] = useState(preferredTemplate)
  if (preferredTemplate && preferredTemplate !== appliedTemplate) {
    setAppliedTemplate(preferredTemplate)
    setTemplateId(preferredTemplate)
  }
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState<Checklist | null>(() => readSaved())
  const [loadError, setLoadError] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    checklistTemplates()
      .then((rows) => {
        if (!active) return
        setTemplates(rows)
        setTemplateId((current) => current || rows[0]?.id || "")
      })
      .catch(() => {
        if (active) setLoadError(true)
      })
    return () => {
      active = false
    }
  }, [])

  const selected = templates.find((item) => item.id === templateId)

  async function onStart() {
    if (!templateId) return
    setBusy(true)
    setError(null)
    try {
      const next = await startChecklist(templateId, answers, language)
      setSaved(next)
      writeSaved(next)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : copy("checklistFailed"))
    } finally {
      setBusy(false)
    }
  }

  async function onToggle(stepId: string, done: boolean) {
    if (!saved) return
    const optimistic = {
      ...saved,
      steps: saved.steps.map((step) => (step.id === stepId ? { ...step, done } : step)),
    }
    const doneCount = optimistic.steps.filter((step) => step.done).length
    optimistic.progress = optimistic.steps.length ? doneCount / optimistic.steps.length : 0
    setSaved(optimistic)
    writeSaved(optimistic)
    try {
      const next = await markChecklistStep(saved.id, stepId, done)
      setSaved(next)
      writeSaved(next)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : copy("checklistFailed"))
    }
  }

  return (
    <section className="mt-8">
      <h2 className="font-statute text-3xl">{copy("checklistTitle")}</h2>
      <p className="mt-2 max-w-[46ch] text-muted">{copy("checklistHelp")}</p>
      <div className="mt-4 grid gap-3">
        <label className="text-sm">
          {copy("checklistTitle")}
          <select
            className={inputClass}
            value={templateId}
            onChange={(event) => {
              setTemplateId(event.target.value)
              setAnswers({})
            }}
          >
            {templates.map((item) => (
              <option key={item.id} value={item.id}>
                {language === "roman_urdu" ? item.title_ru : item.title}
              </option>
            ))}
          </select>
        </label>
        {selected?.questions.map((question) => (
          <label key={question.id} className="text-sm">
            {language === "roman_urdu" ? question.prompt_ru : question.prompt}
            <select
              className={inputClass}
              value={answers[question.id] ?? ""}
              onChange={(event) =>
                setAnswers((current) => ({ ...current, [question.id]: event.target.value }))
              }
            >
              <option value="" />
              {question.options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        ))}
        <button type="button" disabled={busy} onClick={onStart} className="min-h-11 bg-seal px-4 text-paper">
          {copy("checklistStart")}
        </button>
      </div>
      {loadError ? <p className="mt-3 text-sm text-low">{copy("checklistFailed")}</p> : null}
      {error ? <p className="mt-3 text-sm text-low">{error}</p> : null}
      {saved ? (
        <div className="mt-6 border border-rule bg-field px-4 py-4">
          <p className="text-lg">{saved.title}</p>
          <p className="mt-1 text-sm text-muted">
            {copy("checklistProgress")}: {Math.round(saved.progress * 100)}%. {copy("checklistSaved")}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" onClick={() => window.print()} className="min-h-11 border border-rule px-3 text-sm">
              {copy("checklistPrint")}
            </button>
            <button
              type="button"
              onClick={() => {
                const text = saved.steps.map((step) => `${step.done ? "[x]" : "[ ]"} ${step.title}`).join("\n")
                void navigator.clipboard.writeText(text).catch(() => undefined)
              }}
              className="min-h-11 border border-rule px-3 text-sm"
            >
              {copy("checklistShare")}
            </button>
          </div>
          <ul className="mt-3 grid gap-3">
            {saved.steps.map((step) => (
              <li key={step.id} className="border border-rule px-3 py-3">
                <label className="flex min-h-11 items-start gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={step.done}
                    onChange={(event) => onToggle(step.id, event.target.checked)}
                  />
                  <span>
                    <span className="font-medium">{step.title}</span>
                    <span className="mt-1 block">{step.detail}</span>
                    <span className="mt-1 block text-muted">{step.sources.join("; ")}</span>
                    {step.link ? (
                      <a href={step.link.url} target="_blank" rel="noopener noreferrer" className="underline">
                        {step.link.label}
                      </a>
                    ) : null}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

function readSaved(): Checklist | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return null
  try {
    const value = JSON.parse(raw) as Checklist
    if (!value || !Array.isArray(value.steps)) return null
    return value
  } catch {
    return null
  }
}

function writeSaved(value: Checklist) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
}
