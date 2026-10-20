/** One answer card: text, sources, agent steps, copy, and feedback. */

import { useState } from "react"
import type { FeedbackReason, Source } from "../../api/chat"
import { annotatePkr, formatPkr } from "../../lib/money"
import { safeHref } from "../../lib/safeUrl"
import type { UiLanguage } from "../../lib/session"
import type { CopyKey } from "../../i18n"
import { localizedError } from "../../i18n/errors"
import RefusalCard from "./RefusalCard"
import { refusalKind } from "./refusal"
import type { Turn } from "./types"

type Copy = (key: CopyKey) => string

const CONFIDENCE = { high: "high", medium: "medium", low: "low" } as const

function hasCitation(sources: Source[]): boolean {
  return sources.some((source) => Boolean(source.section || source.url || source.snippet))
}

export default function AnswerSlip({
  turn,
  copy,
  language,
  onFeedback,
  onAsk,
}: {
  turn: Turn
  copy: Copy
  language: UiLanguage
  onFeedback: (rating: "up" | "down", reason: FeedbackReason | null) => void
  onAsk: (question: string) => void
}) {
  const [reasonsOpen, setReasonsOpen] = useState(false)
  const final = turn.final
  const cited = hasCitation(turn.sources)
  const library = final && cited ? final.answer_source : "none"
  const verified = Boolean(final?.verified) && cited
  const confidence = final && cited ? final.confidence : "low"
  const kind = final ? refusalKind(turn.intent, final.answer_source, final.model) : null
  const text = final ? annotatePkr(localizedError(final.answer, language)) : turn.draft
  const waiting = !text && !turn.error && !kind && turn.sources.length === 0 && !turn.toolCard

  return (
    <article>
      <div className="min-w-0 max-w-[70ch]">
      {waiting ? (
        <div className="mt-2 grid gap-2" aria-hidden="true">
          <div className="waiting h-4 w-4/5" />
          <div className="waiting h-4 w-full" />
          <div className="waiting h-4 w-2/3" />
        </div>
      ) : null}

      {!final && turn.sources.length > 0 ? (
        <section data-motion-slot="sources-strip" aria-label={copy("sources")} className="mb-4">
          <p className="text-sm font-medium text-muted">{copy("checkingSources")}</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {turn.sources.map((source, index) => (
              <div key={`${source.doc_id}-${index}`} className="border border-rule bg-field px-3 py-2 text-sm">
                <p className="font-medium text-seal">
                  {source.section ? `${copy("section")} ${source.section}` : source.title}
                </p>
                <p className="text-muted">{source.title}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {text && !kind ? (
        <p className="max-w-[68ch] whitespace-pre-wrap leading-relaxed">
          {text}
          {!final ? <span className="caret" aria-hidden="true" /> : null}
        </p>
      ) : null}

      {kind && final ? (
        <RefusalCard
          kind={kind}
          reason={localizedError(final.answer, language)}
          authority={final.action_links.find((link) => link.authority)?.authority ?? null}
          query={final.trace?.search_query ?? null}
          retrieved={final.trace?.retrieved ?? null}
          suggestions={final.follow_ups}
          links={final.action_links}
          copy={copy}
          onAsk={onAsk}
        />
      ) : null}

          {turn.toolCard ? <ToolCard card={turn.toolCard} copy={copy} language={language} /> : null}
          {turn.toolNote && !turn.toolCard ? (
            <p className="mt-4 text-sm text-muted">{copy("toolLater")}</p>
          ) : null}

          {final && !kind ? (
            <div className="mt-5">
              <p
                className={
                  library === "verified"
                    ? "text-sm font-medium text-seal"
                    : library === "web"
                      ? "text-sm font-medium text-web"
                      : "text-sm text-muted"
                }
              >
                {copy(
                  library === "verified"
                    ? "libraryVerified"
                    : library === "web"
                      ? "libraryWeb"
                      : "libraryNone",
                )}
              </p>
              <dl className="mt-4 grid gap-3 border-t border-rule pt-3 sm:grid-cols-3">
                <div>
                  <dt className="text-xs text-muted">{copy("confidence")}</dt>
                  <dd className="text-sm">{copy(CONFIDENCE[confidence])}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">{copy("verified")}</dt>
                  <dd className={`text-sm ${verified ? "text-seal" : "text-low"}`}>
                    {verified ? copy("verifiedYes") : copy("notVerified")}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">{copy("taxYear")}</dt>
                  <dd className="text-sm">
                    {final.tax_year}. {final.answer_source === "web" ? copy("pageChecked") : copy("lawAsOf")}{" "}
                    {formatWhen(final.corpus_date)}
                  </dd>
                </div>
              </dl>
              {final.cached ? <p className="text-sm text-muted">{copy("cachedAnswer")}</p> : null}
              {final.model && final.model !== "none" ? (
                <p className="text-sm text-muted">
                  {copy("answeredBy")} {final.model}
                </p>
              ) : null}
            </div>
          ) : null}

      {final ? (
        <div className="mt-5 border-t border-rule pt-4">
          {!kind && final.follow_ups.length > 0 ? (
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

          <AgentSteps turn={turn} copy={copy} language={language} />
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
      </div>
    </article>
  )
}

export function SourcesRail({
  turn,
  language,
  copy,
  className = "",
}: {
  turn: Turn
  language: UiLanguage
  copy: Copy
  className?: string
}) {
  const final = turn.final
  if (!final) return null
  return (
    <aside className={`mt-6 border-t border-rule pt-4 xl:border-t-0 xl:border-l xl:pt-0 xl:pl-6 ${className}`}>
      <h3 className="text-xs font-medium tracking-[0.14em] text-muted">{copy("sources")}</h3>
      {turn.sources.length === 0 ? (
        <p className="mt-3 text-sm leading-relaxed text-muted">{copy("noSection")}</p>
      ) : (
        <ol className="mt-3 grid gap-4">
          {turn.sources.map((source, index) => (
            <li key={`${source.doc_id}-${index}`} className="border-t border-rule pt-3">
              <SourceLine source={source} taxYear={final.tax_year} corpusDate={final.corpus_date} copy={copy} />
            </li>
          ))}
        </ol>
      )}
      {final.action_links.some((link) => link.url) ? (
        <div className="mt-5">
          <h3 className="text-xs font-medium tracking-[0.14em] text-muted">{copy("officialPages")}</h3>
          <ul className="mt-3 grid gap-2">
            {final.action_links
              .filter((link) => safeHref(link.url))
              .map((link) => (
                <li key={link.url}>
                  <a
                    href={safeHref(link.url) ?? undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-seal underline decoration-rule underline-offset-4 hover:decoration-seal"
                  >
                    {language === "roman_urdu" && link.label_ru ? link.label_ru : link.label}
                    <span className="text-muted"> · {link.authority}</span>
                    <span className="sr-only"> {copy("opensOfficial")}</span>
                  </a>
                </li>
              ))}
          </ul>
        </div>
      ) : null}
    </aside>
  )
}

function AgentSteps({ turn, copy, language }: { turn: Turn; copy: Copy; language: UiLanguage }) {
  const [note, setNote] = useState<string | null>(null)
  const trace = turn.final?.trace
  const answer = localizedError(turn.final?.answer || turn.draft, language)

  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(answer)
      setNote(copy("copied"))
    } catch {
      setNote(copy("shareFailed"))
    }
  }

  async function shareAnswer() {
    const payload = { title: "DaleelAI", text: answer }
    if (typeof navigator.share === "function") {
      try {
        await navigator.share(payload)
        return
      } catch {
        return
      }
    }
    await copyAnswer()
  }

  return (
    <div className="mt-5">
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => void copyAnswer()} className="min-h-11 border border-rule px-3 text-sm">
          {copy("copyAnswer")}
        </button>
        <button type="button" onClick={() => void shareAnswer()} className="min-h-11 border border-rule px-3 text-sm">
          {copy("shareAnswer")}
        </button>
      </div>
      {note ? <p className="mt-2 text-sm text-muted">{note}</p> : null}
      <details className="mt-3 border border-rule bg-paper px-3 py-2 text-sm">
        <summary className="min-h-11 cursor-pointer">{copy("agentSteps")}</summary>
        {trace ? (
          <dl className="mt-2 grid gap-1">
            <div>
              <dt className="inline text-muted">{copy("stepIntent")} </dt>
              <dd className="inline">{trace.intent}</dd>
            </div>
            <div>
              <dt className="inline text-muted">{copy("stepQuery")} </dt>
              <dd className="inline">{trace.search_query}</dd>
            </div>
            <div>
              <dt className="inline text-muted">{copy("stepRetrieved")} </dt>
              <dd className="inline">{trace.retrieved ?? 0}</dd>
            </div>
            <div>
              <dt className="inline text-muted">{copy("stepRerank")} </dt>
              <dd className="inline">{trace.rerank_top ?? copy("stepNone")}</dd>
            </div>
            <div>
              <dt className="inline text-muted">{copy("stepVerified")} </dt>
              <dd className="inline">
                {hasCitation(turn.sources) && trace.verified ? copy("stepYes") : copy("stepNo")}
              </dd>
            </div>
            <div>
              <dt className="inline text-muted">{copy("stepLatency")} </dt>
              <dd className="inline">{trace.latency_ms ?? 0} ms</dd>
            </div>
          </dl>
        ) : (
          <p className="mt-2 text-muted">{turn.intent ?? copy("stepNone")}</p>
        )}
      </details>
    </div>
  )
}

function ToolCard({
  card,
  copy,
  language,
}: {
  card: NonNullable<Turn["toolCard"]>
  copy: Copy
  language: UiLanguage
}) {
  const data = card.data
  const rows = Array.isArray(data.rows) ? (data.rows as Record<string, unknown>[]) : []
  const lines = Array.isArray(data.breakdown) ? (data.breakdown as Record<string, unknown>[]) : []
  return (
    <div className="panel mt-4 px-4 py-3">
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
      {typeof data.advice === "string" ? (
        <p className="mt-2 text-sm">
          {language === "roman_urdu" && typeof data.advice_ru === "string" ? data.advice_ru : data.advice}
        </p>
      ) : null}
      {typeof data.disclaimer === "string" ? (
        <p className="mt-2 text-sm text-muted">{data.disclaimer}</p>
      ) : null}
      {Array.isArray(data.items) ? (
        <ul className="mt-2 grid gap-2 text-sm">
          {(data.items as { id?: string; title?: string; source_url?: string }[]).map((item) => (
            <li key={item.id ?? item.title}>
              {safeHref(item.source_url) ? (
                <a href={safeHref(item.source_url) ?? undefined} className="underline" target="_blank" rel="noopener noreferrer">
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
  const href = safeHref(source.url) || safeHref(source.mirror_url)
  const when = source.library === "web" ? (source.fetched_at ?? corpusDate) : corpusDate
  const label = source.section ? `${copy("section")} ${source.section}` : source.title
  const bits = [
    source.page != null ? `${copy("page")} ${source.page}` : "",
    `${copy("taxYear")} ${taxYear}`,
    `${source.library === "web" ? copy("pageChecked") : copy("lawAsOf")} ${formatWhen(when)}`,
  ].filter(Boolean)
  const chip = "text-sm font-medium text-seal underline decoration-seal/30 underline-offset-4"
  const title = href ? (
    <a href={href} target="_blank" rel="noopener noreferrer" className={chip}>
      {label}
      <span className="sr-only"> {copy("opensOfficial")}</span>
    </a>
  ) : (
    <span className="text-sm font-medium">{label}</span>
  )
  return (
    <div className="rounded-2xl border border-rule bg-field px-4 py-3">
      {title}
      <p className="mt-1 text-sm text-muted">{source.title}</p>
      <p className="text-sm text-muted">{bits.join(", ")}</p>
      {source.snippet ? <p className="mt-1 max-w-[68ch] text-sm">{source.snippet}</p> : null}
    </div>
  )
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
