/** One answer: sources strip, Markdown body with citation chips, how it was answered, follow-ups, actions. */

import { type ReactNode } from "react"
import type { FeedbackReason } from "../../api/chat"
import { annotatePkr, formatPkr } from "../../lib/money"
import { safeHref } from "../../lib/safeUrl"
import type { UiLanguage } from "../../lib/session"
import type { CopyKey } from "../../i18n"
import { localizedError } from "../../i18n/errors"
import Icon from "../../shell/icons"
import RefusalCard from "./RefusalCard"
import { refusalKind } from "./refusal"
import type { Turn } from "./types"
import AnswerActions from "./answer/AnswerActions"
import AnswerBody from "./answer/AnswerBody"
import HowAnswered from "./answer/HowAnswered"
import SourcesStrip from "./answer/SourcesStrip"
import { citable, citedNumbers, fill, formatDate, fullRef } from "./answer/refs"
import type { OpenSource } from "./answer/types"
import { ChecklistCard, ExpertsCard, FilerCard, NoticeCard, UpdatesCard } from "./toolcards/cards"
import { HIDES_ANSWER } from "./toolcards/toolCards"
import "./toolcards/toolcards.css"

type Copy = (key: CopyKey) => string

export default function AnswerSlip({
  turn,
  copy,
  language,
  lead,
  activeCite,
  onOpen,
  onFeedback,
  onAsk,
  onToast,
}: {
  turn: Turn
  copy: Copy
  language: UiLanguage
  /** Status steps, errors and the like, shown at the top of the answer row. */
  lead?: ReactNode
  activeCite: number | null
  onOpen: OpenSource
  onFeedback: (rating: "up" | "down", reason: FeedbackReason | null, comment: string | null) => void
  onAsk: (question: string) => void
  onToast: (message: string) => void
}) {
  const final = turn.final
  const cited = citable(turn.sources).length > 0
  const kind = final ? refusalKind(turn.intent, final.answer_source, final.model) : null
  const tool = turn.toolCard
  const hideText = Boolean(tool && HIDES_ANSWER.has(tool.type))
  const text = hideText ? "" : final ? annotatePkr(localizedError(final.answer, language)) : turn.draft
  const waiting = !text && !hideText && !turn.error && !kind && turn.sources.length === 0 && !turn.toolCard
  const markers = citedNumbers(text, turn.sources.length)
  const year = (final?.tax_year ?? turn.taxYear ?? "").replace(/^TY/, "")
  const showStrip = !kind && (turn.sources.length > 0 || Boolean(final && !turn.toolCard))
  const copyText = [
    text,
    turn.sources.length
      ? `${copy("sources")}:\n${turn.sources.map((source, index) => `[${index + 1}] ${fullRef(source)}`).join("\n")}`
      : "",
  ]
    .filter(Boolean)
    .join("\n\n")

  return (
    <article className="min-w-0">
      {showStrip ? (
        <SourcesStrip
          sources={turn.sources}
          final={final}
          cited={cited}
          turnId={turn.id}
          activeCite={activeCite}
          copy={copy}
          onOpen={onOpen}
        />
      ) : null}
      <div className="mt-4 flex min-w-0 gap-3">
        <span className="mt-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-seal text-seal-ink" aria-hidden="true">
          <Icon name="doc" size="sm" />
        </span>
        <div className="min-w-0 max-w-[70ch] flex-1">
          {lead}
          {waiting ? (
            <div className="mt-2 grid gap-2" aria-hidden="true">
              <div className="waiting h-4 w-4/5" />
              <div className="waiting h-4 w-full" />
              <div className="waiting h-4 w-2/3" />
            </div>
          ) : null}

          {final && !kind && year && !tool ? (
            <p className="ameta">
              {final.answer_source === "web"
                ? `${copy("taxYear")} ${year} · ${fill(copy("checkedOn"), { date: formatDate(turn.sources.find((source) => source.library === "web")?.fetched_at ?? final.corpus_date) })}`
                : fill(copy("metaLine"), { year, date: formatDate(final.corpus_date) })}
              {final.cached ? ` · ${copy("cachedAnswer")}` : ""}
            </p>
          ) : null}

          {tool ? <ToolCardFor card={tool} copy={copy} language={language} /> : null}
          {text && !kind ? (
            <AnswerBody
              text={text}
              sources={turn.sources}
              turnId={turn.id}
              activeCite={activeCite}
              streaming={!final}
              lang={language === "roman_urdu" ? "ur-Latn" : "en"}
              copy={copy}
              onOpen={onOpen}
            />
          ) : null}

          {kind && final ? (
            <RefusalCard
              kind={kind}
              reason={localizedError(final.answer, language)}
              authority={final.action_links.find((link) => link.authority)?.authority ?? null}
              query={final.trace?.search_query ?? null}
              retrieved={final.trace?.retrieved ?? null}
              rerankTop={final.trace?.rerank_top ?? null}
              suggestions={final.follow_ups}
              links={final.action_links}
              copy={copy}
              onAsk={onAsk}
            />
          ) : null}

          {turn.toolNote && !turn.toolCard ? <p className="mt-4 text-sm text-muted">{copy("toolLater")}</p> : null}

          {final && !kind && !tool ? (
            <HowAnswered
              final={final}
              kept={turn.sources.filter((source) => source.library !== "web").length}
              cited={markers.length}
              copy={copy}
            />
          ) : null}

          {final && !kind && final.follow_ups.length > 0 ? (
            <>
              <h3 className="fu-h">{copy("followUps")}</h3>
              <div className="fus">
                {final.follow_ups.map((question) => (
                  <button key={question} type="button" className="fu" onClick={() => onAsk(question)}>
                    {question}
                    <Icon name="arrow" size="sm" />
                  </button>
                ))}
              </div>
            </>
          ) : null}

          {final && !kind && final.action_links.some((link) => safeHref(link.url)) ? (
            <div className="mt-5">
              <h3 className="fu-h">{copy("officialPages")}</h3>
              <ul className="mt-2 grid gap-2">
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

          {final ? (
            <AnswerActions
              copyText={copyText}
              canRate={Boolean(turn.messageId)}
              feedback={turn.feedback}
              feedbackNote={turn.feedbackNote}
              copy={copy}
              onToast={onToast}
              onFeedback={onFeedback}
            />
          ) : null}
        </div>
      </div>
    </article>
  )
}

/** PR 5b cards by tool_result type; the calculator keeps its plain card until PR 6; unknown types show nothing. */
function ToolCardFor({ card, copy, language }: { card: NonNullable<Turn["toolCard"]>; copy: Copy; language: UiLanguage }) {
  if (card.type === "filer_comparison") return <FilerCard data={card.data} copy={copy} />
  if (card.type === "notice") return <NoticeCard copy={copy} />
  if (card.type === "checklist") return <ChecklistCard data={card.data} copy={copy} language={language} />
  if (card.type === "experts") return <ExpertsCard data={card.data} copy={copy} language={language} />
  if (card.type === "updates") return <UpdatesCard data={card.data} copy={copy} />
  if (card.type === "calculation") return <ToolCard card={card} copy={copy} language={language} />
  return null
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
