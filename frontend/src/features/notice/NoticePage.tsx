import { useState, type FormEvent } from "react"
import { explainNotice, type NoticeExplanation } from "../../api/phase5"
import type { CopyKey } from "../../i18n"
import type { UiLanguage } from "../../lib/session"

type Copy = (key: CopyKey) => string

const inputClass = "mt-1 min-h-11 w-full border border-rule bg-field px-3 text-base text-ink"

export default function NoticePage({ copy, language }: { copy: Copy; language: UiLanguage }) {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<NoticeExplanation | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!file) {
      setError(copy("noticeFile"))
      return
    }
    setBusy(true)
    setError(null)
    try {
      setResult(await explainNotice(file, language))
    } catch (caught) {
      setResult(null)
      setError(caught instanceof Error ? caught.message : copy("noticeFailed"))
    } finally {
      setBusy(false)
    }
  }

  const explanation = result?.explanation
  return (
    <section className="mt-8">
      <h2 className="font-statute text-3xl">{copy("noticeTitle")}</h2>
      <p className="mt-2 max-w-[46ch] text-muted">{copy("noticeHelp")}</p>
      <form onSubmit={onSubmit} className="mt-4 grid gap-3">
        <label className="text-sm">
          {copy("noticeFile")}
          <input
            className={inputClass}
            type="file"
            accept="application/pdf,image/png,image/jpeg"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <button type="submit" disabled={busy} className="min-h-11 bg-seal px-4 text-paper">
          {copy("noticeExplain")}
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-low">{error}</p> : null}
      {result && explanation ? (
        <div className="mt-6 border border-rule bg-field px-4 py-4">
          <p className="text-lg">{explanation.summary}</p>
          <p className="mt-2">{explanation.why_received}</p>
          <p className="mt-3 text-sm text-muted">
            {result.law}
            {result.section ? `, section ${result.section}` : ""}
            {result.tax_year ? `, ${result.tax_year}` : ""}
          </p>
          {result.deadline ? (
            <p className="mt-2 text-sm">
              {copy("noticeDeadline")}: {result.deadline}
              {explanation.days_left != null ? ` (${copy("noticeDays")}: ${explanation.days_left})` : ""}
            </p>
          ) : null}
          {explanation.recommend_expert ? <p className="mt-2 text-sm">{copy("noticeExpert")}</p> : null}
          <ul className="mt-3 grid gap-1 text-sm">
            {explanation.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
          <h3 className="mt-4 text-sm font-medium">{copy("noticeSources")}</h3>
          <ul className="mt-1 grid gap-2 text-sm">
            {result.sources.map((source, index) => (
              <li key={index}>
                {source.title}
                {source.section ? `, section ${source.section}` : ""}. {source.snippet}
              </li>
            ))}
          </ul>
          {result.action_links.length > 0 ? (
            <ul className="mt-3 grid gap-1 text-sm">
              {result.action_links.map((link) => (
                <li key={link.url}>
                  <a href={link.url} target="_blank" rel="noopener noreferrer" className="underline">
                    {language === "roman_urdu" ? link.label_ru : link.label}
                  </a>
                </li>
              ))}
            </ul>
          ) : null}
          <p className="mt-3 text-sm text-muted">
            {copy("noticeRedactions")}: CNIC {result.redactions.cnic ?? 0}, NTN {result.redactions.ntn ?? 0}
          </p>
        </div>
      ) : null}
    </section>
  )
}
