import { useState, type FormEvent } from "react"
import { explainNotice, type NoticeExplanation } from "../../api/phase5"
import type { CopyKey } from "../../i18n"
import type { UiLanguage } from "../../lib/session"
import { primary, secondary } from "../../ui/styles"

type Copy = (key: CopyKey) => string

export default function NoticePage({
  copy,
  language,
  onFindExpert,
}: {
  copy: Copy
  language: UiLanguage
  onFindExpert?: (category: string) => void
}) {
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
    <section>
      <h2 className="font-statute text-3xl tracking-tight">{copy("noticeTitle")}</h2>
      <p className="mt-2 max-w-[58ch] text-sm leading-6 text-muted">{copy("noticeHelp")}</p>
      <form onSubmit={(event) => void onSubmit(event)} className="mt-5 grid gap-3">
        <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-rule bg-field px-4 py-8 text-center">
          <span className="text-sm font-medium">{file ? file.name : copy("noticeFile")}</span>
          <span className="mt-1 text-sm text-muted">{copy("noticeDrop")}</span>
          <input
            className="sr-only"
            type="file"
            accept="application/pdf,image/png,image/jpeg"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null)
              setError(null)
            }}
          />
        </label>
        <button type="submit" disabled={busy} className={`${primary} w-full sm:w-auto`}>
          {busy ? copy("noticeReading") : copy("noticeExplain")}
        </button>
      </form>
      {error ? (
        <p className="mt-3 text-sm text-low" role="alert">
          {error}
        </p>
      ) : null}
      {result && explanation ? (
        <div className="mt-6 rounded-2xl border border-rule bg-field px-5 py-5 shadow-[0_1px_2px_rgba(26,24,20,0.04),0_18px_40px_rgba(26,24,20,0.05)]">
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
            </p>
          ) : null}
          {explanation.days_left != null ? (
            <p
              className={`mt-2 inline-block border border-rule px-2 py-1 text-sm ${
                explanation.days_left <= 7 ? "text-low" : "text-ink"
              }`}
            >
              {copy("noticeCountdown")}: {explanation.days_left}
            </p>
          ) : null}
          {explanation.recommend_expert ? <p className="mt-2 text-sm">{copy("noticeExpert")}</p> : null}
          {result.expert_category && onFindExpert ? (
            <button
              type="button"
              className={`${secondary} mt-3`}
              onClick={() => onFindExpert(result.expert_category ?? "")}
            >
              {copy("noticeFindMatching")} ({result.expert_category})
            </button>
          ) : null}
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
