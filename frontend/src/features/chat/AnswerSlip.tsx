import { useState } from "react"
import type { FeedbackReason, Source } from "../../api/chat"
import { annotatePkr, formatPkr } from "../../lib/money"
import type { UiLanguage } from "../../lib/session"
import type { CopyKey } from "../../i18n"
import type { Turn } from "./types"

type Copy = (key: CopyKey) => string

const CONFIDENCE = { high: "high", medium: "medium", low: "low" } as const

export default function AnswerSlip({
  turn,
  language,
  copy,
  onFeedback,
  onAsk,
}: {
  turn: Turn
  language: UiLanguage
  copy: Copy
  onFeedback: (rating: "up" | "down", reason: FeedbackReason | null) => void
  onAsk: (question: string) => void
}) {
  const [reasonsOpen, setReasonsOpen] = useState(false)
  const final = turn.final
  const text = final ? annotatePkr(final.answer) : turn.draft
  const taxYear = final?.tax_year ?? turn.taxYear
  const waiting = !text && !turn.error

  return (
    <article className="mt-6 border border-rule bg-field">
      <div className="grid grid-cols-[4.5rem_minmax(0,1fr)]">
        <div className="border-r border-rule px-2 py-4 text-sm text-muted">{margin(turn.sources, taxYear)}</div>
        <div className="min-w-0 px-4 py-4">
          <p className="text-sm text-muted">{copy("you")}</p>
          <p className="max-w-[68ch]">{turn.question}</p>
          {turn.redacted ? <p className="mt-1 text-sm text-muted">{copy("redactionSent")}</p> : null}

          {turn.status ? (
            <p className="mt-4 text-sm text-muted" aria-live="polite">
              {turn.status}
            </p>
          ) : null}

          {waiting ? (
            <div className="mt-4 grid gap-2" aria-hidden="true">
              <div className="waiting h-4 w-4/5" />
              <div className="waiting h-4 w-full" />
              <div className="waiting h-4 w-2/3" />
            </div>
          ) : null}

          {text ? (
            <p className="statute mt-4 max-w-[68ch] text-lg whitespace-pre-wrap">{text}</p>
          ) : null}

          {turn.error ? (
            <p className="mt-4 text-sm text-low" role="alert">
              {turn.error}
            </p>
          ) : null}

          {turn.toolCard ? <ToolCard card={turn.toolCard} copy={copy} /> : null}
          {turn.toolNote && !turn.toolCard ? (
            <p className="mt-4 text-sm text-muted">{copy("toolLater")}</p>
          ) : null}

          {final ? (
            <div className="mt-5">
              <p
                className={
                  final.answer_source === "verified"
                    ? "seal-in inline-block border-2 border-double border-seal bg-seal px-2 py-1 text-sm text-seal-ink"
                    : final.answer_source === "web"
                      ? "seal-in inline-block border-2 border-double border-web px-2 py-1 text-sm text-web"
                      : "seal-in inline-block border border-rule px-2 py-1 text-sm text-muted"
                }
              >
                {copy(
                  final.answer_source === "verified"
                    ? "libraryVerified"
                    : final.answer_source === "web"
                      ? "libraryWeb"
                      : "libraryNone",
                )}
              </p>
              <p className="mt-3 text-sm">
                {copy("confidence")}: {copy(CONFIDENCE[final.confidence])}
              </p>
              <p className={`text-sm ${final.verified ? "text-seal" : "text-low"}`}>
                {final.verified ? copy("verified") : copy("notVerified")}
              </p>
              <p className="text-sm text-muted">
                {copy("taxYear")} {final.tax_year}.{" "}
                {final.answer_source === "web" ? copy("pageChecked") : copy("lawAsOf")}{" "}
                {formatWhen(final.corpus_date)}
              </p>
              {final.cached ? <p className="text-sm text-muted">{copy("cachedAnswer")}</p> : null}
              {final.model && final.model !== "none" ? (
                <p className="text-sm text-muted">
                  {copy("answeredBy")} {final.model}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {final ? (
        <div className="border-t border-rule px-4 py-4">
          <h3 className="text-base font-medium">{copy("sources")}</h3>
          {turn.sources.length === 0 ? (
            <p className="mt-2 text-sm text-muted">{copy("noSection")}</p>
          ) : (
            <ol className="mt-3 grid gap-4">
              {turn.sources.map((source, index) => (
                <li key={`${source.doc_id}-${index}`}>
                  <SourceLine source={source} taxYear={final.tax_year} corpusDate={final.corpus_date} copy={copy} />
                </li>
              ))}
            </ol>
          )}

          {final.action_links.some((link) => link.url) ? (
            <div className="mt-5">
              <h3 className="text-base font-medium">{copy("officialPages")}</h3>
              <ul className="mt-2 grid gap-2">
                {final.action_links
                  .filter((link) => link.url)
                  .map((link) => (
                    <li key={link.url}>
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex min-h-11 items-center underline decoration-rule underline-offset-4"
                      >
                        {language === "roman_urdu" && link.label_ru ? link.label_ru : link.label} ({link.authority})
                        <span className="sr-only"> {copy("opensOfficial")}</span>
                      </a>
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}

          {final.follow_ups.length > 0 ? (
            <div className="mt-5">
              <h3 className="text-base font-medium">{copy("related")}</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {final.follow_ups.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => onAsk(question)}
                    className="min-h-11 border border-rule bg-paper px-3 text-left text-sm transition-opacity duration-150 hover:opacity-80"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <p className="mt-5 max-w-[68ch] text-sm text-muted">{copy("disclaimer")}</p>

          {turn.messageId ? (
            <div className="mt-4">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  aria-pressed={turn.feedback === "up"}
                  disabled={turn.feedback !== null}
                  onClick={() => onFeedback("up", null)}
                  className="min-h-11 border border-rule px-3 text-sm transition-opacity duration-150 hover:opacity-80 disabled:text-muted"
                >
                  {copy("helpful")}
                </button>
                <button
                  type="button"
                  aria-pressed={turn.feedback === "down"}
                  disabled={turn.feedback !== null}
                  onClick={() => {
                    setReasonsOpen(true)
                    onFeedback("down", null)
                  }}
                  className="min-h-11 border border-rule px-3 text-sm transition-opacity duration-150 hover:opacity-80 disabled:text-muted"
                >
                  {copy("notHelpful")}
                </button>
              </div>
              {reasonsOpen ? (
                <div className="mt-3">
                  <p className="text-sm">{copy("whatWasWrong")}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(["wrong", "incomplete", "outdated", "other"] as const).map((reason) => (
                      <button
                        key={reason}
                        type="button"
                        onClick={() => onFeedback("down", reason)}
                        className="min-h-11 border border-rule px-3 text-sm"
                      >
                        {copy(reason)}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
              {turn.feedbackNote ? <p className="mt-2 text-sm text-muted">{turn.feedbackNote}</p> : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}

function ToolCard({
  card,
  copy,
}: {
  card: NonNullable<Turn["toolCard"]>
  copy: Copy
}) {
  const data = card.data
  const rows = Array.isArray(data.rows) ? (data.rows as Record<string, unknown>[]) : []
  const lines = Array.isArray(data.breakdown) ? (data.breakdown as Record<string, unknown>[]) : []
  return (
    <div className="mt-4 border border-rule bg-field px-3 py-3">
      <p className="text-sm font-medium">
        {copy(
          card.type === "filer_comparison"
            ? "filerTitle"
            : card.type === "notice"
              ? "noticeTitle"
              : card.type === "checklist"
                ? "checklistTitle"
                : card.type === "experts"
                  ? "expertsTitle"
                  : card.type === "updates"
                    ? "updatesTitle"
                    : "calcTitle",
        )}
      </p>
      {typeof data.message === "string" ? <p className="mt-2 text-sm">{data.message}</p> : null}
      {typeof data.title === "string" ? <p className="mt-2">{data.title}</p> : null}
      {typeof data.advice === "string" ? <p className="mt-2 text-sm">{data.advice}</p> : null}
      {typeof data.disclaimer === "string" ? (
        <p className="mt-2 text-sm text-muted">{data.disclaimer}</p>
      ) : null}
      {Array.isArray(data.items) ? (
        <ul className="mt-2 grid gap-2 text-sm">
          {(data.items as { id?: string; title?: string; source_url?: string }[]).map((item) => (
            <li key={item.id ?? item.title}>
              {item.source_url ? (
                <a href={item.source_url} className="underline" target="_blank" rel="noopener noreferrer">
                  {item.title}
                </a>
              ) : (
                item.title
              )}
            </li>
          ))}
        </ul>
      ) : null}
      {typeof data.progress === "number" ? (
        <p className="text-sm text-muted">
          {copy("checklistProgress")} {Math.round(data.progress * 100)}%
        </p>
      ) : null}
      {typeof data.total_tax === "number" ? (
        <p className="mt-2 text-lg">{formatPkr(data.total_tax)}</p>
      ) : null}
      {typeof data.monthly_tax === "number" ? (
        <p className="text-sm text-muted">
          {copy("monthlyTax")} {formatPkr(data.monthly_tax)}
        </p>
      ) : null}
      {lines.length > 0 ? (
        <ul className="mt-2 grid gap-1 text-sm">
          {lines.map((line, index) => (
            <li key={index}>
              {String(line.label)}: {formatPkr(Number(line.tax))}
            </li>
          ))}
        </ul>
      ) : null}
      {rows.length > 0 ? (
        <ul className="mt-2 grid gap-1 text-sm">
          {rows.map((row, index) => (
            <li key={index}>
              {String(row.type)}: {copy("filer")} {formatPkr(Number(row.filer_tax))}, {copy("nonFiler")}{" "}
              {formatPkr(Number(row.non_filer_tax))}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

function SourceLine({
  source,
  taxYear,
  corpusDate,
  copy,
}: {
  source: Source
  taxYear: string
  corpusDate: string
  copy: Copy
}) {
  const href = source.url || source.mirror_url || ""
  const when = source.library === "web" ? (source.fetched_at ?? corpusDate) : corpusDate
  const bits = [
    source.section ? `${copy("section")} ${source.section}` : "",
    source.page != null ? `${copy("page")} ${source.page}` : "",
    `${copy("taxYear")} ${taxYear}`,
    `${source.library === "web" ? copy("pageChecked") : copy("lawAsOf")} ${formatWhen(when)}`,
  ].filter(Boolean)
  const title = href ? (
    <a href={href} target="_blank" rel="noopener noreferrer" className="underline decoration-rule underline-offset-4">
      {source.title}
      <span className="sr-only"> {copy("opensOfficial")}</span>
    </a>
  ) : (
    source.title
  )
  return (
    <div>
      <p className="font-medium">{title}</p>
      <p className="text-sm text-muted">{bits.join(", ")}</p>
      {source.snippet ? <p className="statute mt-1 max-w-[68ch] text-sm">{source.snippet}</p> : null}
    </div>
  )
}

function margin(sources: Source[], taxYear: string | null): string {
  const section = sources.find((source) => source.section && /^\d+[A-Za-z]?$/.test(source.section))?.section
  if (section) return `s. ${section}`
  return taxYear ?? ""
}

function formatWhen(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Karachi",
  }).format(date)
}
