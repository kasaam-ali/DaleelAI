/** In-chat tool cards for the real tool_result shapes (SPEC §5.9). */

import type { CSSProperties } from "react"
import type { CopyKey } from "../../../i18n"
import { formatPkr } from "../../../lib/money"
import { safeHref } from "../../../lib/safeUrl"
import type { UiLanguage } from "../../../lib/session"
import Icon from "../../../shell/icons"
import { categoryLabel } from "../../experts/ExpertsPage"
import { fill, formatDate } from "../answer/refs"
import ToolCardFrame, { CardFoot } from "./ToolCardFrame"

type Copy = (key: CopyKey) => string
type Data = Record<string, unknown>

type CompareRow = {
  type: string
  amount: number
  filer_tax: number
  late_filer_tax: number | null
  non_filer_tax: number
  source?: { law?: string; ref?: string }
}

export function FilerCard({ data, copy }: { data: Data; copy: Copy }) {
  const rows = Array.isArray(data.rows) ? (data.rows as CompareRow[]) : []
  const law = rows.find((row) => row.source?.law)?.source?.law
  return (
    <ToolCardFrame
      kind="filer_comparison"
      icon="checkShield"
      label={copy("tcFilerTitle")}
      link={{ href: "#/filer", text: copy("tcOpenFiler") }}
    >
      <div className="cb">
        <small className="m-0">{copy("tcFilerHelp")}</small>
      </div>
      {rows.map((row, index) => {
        const bars: [string, number, string][] = [
          [copy("filer"), row.filer_tax, "var(--seal)"],
          ...(row.late_filer_tax != null ? ([[copy("lateFiler"), row.late_filer_tax, "var(--warning)"]] as [string, number, string][]) : []),
          [copy("nonFiler"), row.non_filer_tax, "var(--warning)"],
        ]
        const max = Math.max(1, ...bars.map((bar) => bar[1]))
        return (
          <div key={`${row.type}-${index}`} className="fc">
            <div className="t">
              {copy(row.type as CopyKey)} · {formatPkr(row.amount)}
            </div>
            {bars.map(([label, value, colour], barIndex) => (
              <div key={label} className="fr">
                <span>{label}</span>
                <i aria-hidden="true">
                  <em style={{ "--w": Math.max(value / max, 0.02), background: colour, animationDelay: `${barIndex * 90}ms` } as CSSProperties} />
                </i>
                <span className="n">{`Rs ${value.toLocaleString("en-US")}`}</span>
              </div>
            ))}
          </div>
        )
      })}
      <CardFoot
        icon="info"
        start={typeof data.rules_version === "string" ? fill(copy("tcRules"), { v: data.rules_version }) : ""}
        end={law ? fill(copy("tcSource"), { law }) : null}
      />
    </ToolCardFrame>
  )
}

export function NoticeCard({ copy }: { copy: Copy }) {
  return (
    <ToolCardFrame kind="notice" icon="notice" label={copy("tcNoticeTitle")}>
      <p className="cp">{copy("noticeHelp")}</p>
      <div className="cb2">
        <a className="btnp" href="#/notice">
          <Icon name="upload" size="sm" />
          {copy("tcUpload")}
        </a>
        <span className="btng" aria-disabled="true">
          {copy("tcPasteSoon")}
        </span>
      </div>
      <div className="nprv">
        <Icon name="lock" size="sm" />
        {copy("tcNoticePrivacy")}
      </div>
    </ToolCardFrame>
  )
}

type Step = { id: string; title: string; title_ru?: string; detail?: string; detail_ru?: string; sources?: string[]; done?: boolean }

export function ChecklistCard({ data, copy, language }: { data: Data; copy: Copy; language: UiLanguage }) {
  const steps = Array.isArray(data.steps) ? (data.steps as Step[]) : []
  const done = steps.filter((step) => step.done).length
  const progress = typeof data.progress === "number" ? data.progress : 0
  const ru = language === "roman_urdu"
  return (
    <ToolCardFrame
      kind="checklist"
      icon="listck"
      label={copy("tcChecklistTitle")}
      link={{ href: "#/checklists", text: copy("tcOpenChecklist") }}
    >
      <div className="cprog">
        <b>{String(data.title ?? "")}</b>
        <span className="bar" aria-hidden="true">
          <em style={{ "--p": progress } as CSSProperties} />
        </span>
        <span className="pc">{Math.round(progress * 100)}%</span>
      </div>
      <ul className="cks" aria-label={fill(copy("tcSteps"), { done, total: steps.length })}>
        {steps.slice(0, 3).map((step) => (
          <li key={step.id}>
            <span className={`bx${step.done ? " on" : ""}`} aria-hidden="true" />
            <span>
              {ru && step.title_ru ? step.title_ru : step.title}
              {step.sources?.[0] ? <small>{step.sources[0]}</small> : null}
            </span>
          </li>
        ))}
      </ul>
      <CardFoot icon="lock" start={`${copy("tcSaved")} · ${fill(copy("tcSteps"), { done, total: steps.length })}`} />
    </ToolCardFrame>
  )
}

type Expert = { id: string; name: string; firm?: string | null; city: string; specialties: string[]; profile_url?: string; last_updated?: string }

export function ExpertsCard({ data, copy, language }: { data: Data; copy: Copy; language: UiLanguage }) {
  const experts = Array.isArray(data.experts) ? (data.experts as Expert[]) : []
  const advice = language === "roman_urdu" && typeof data.advice_ru === "string" ? data.advice_ru : data.advice
  const updated = experts.map((expert) => expert.last_updated).filter(Boolean).sort().at(-1)
  return (
    <ToolCardFrame
      kind="experts"
      icon="briefcase"
      label={copy("tcExpertsTitle")}
      link={{ href: "#/experts", text: copy("tcSeeAll") }}
    >
      {typeof advice === "string" ? <p className="cp">{advice}</p> : null}
      {experts.slice(0, 2).map((expert) => {
        const href = safeHref(expert.profile_url)
        return (
          <div key={expert.id} className="xr">
            <b>{expert.name}</b>
            <small>
              {expert.city} · {expert.specialties.map((item) => categoryLabel(item, copy)).join(", ")}
            </small>
            {href ? (
              <a href={href} target="_blank" rel="noopener noreferrer" aria-label={`${copy("tcViewListing")}: ${expert.name}`}>
                {copy("tcViewListing")}
                <Icon name="ext" size="sm" />
              </a>
            ) : null}
          </div>
        )
      })}
      <CardFoot
        icon="info"
        start={copy("tcNotEndorsement")}
        end={updated ? fill(copy("tcUpdated"), { date: formatDate(updated) }) : null}
      />
    </ToolCardFrame>
  )
}

type Update = { id: string; title: string; doc_type: string; published_at?: string | null; source_url?: string }

export function UpdatesCard({ data, copy }: { data: Data; copy: Copy }) {
  const items = Array.isArray(data.items) ? (data.items as Update[]) : []
  const total = typeof data.total === "number" ? data.total : items.length
  const shown = items.slice(0, 3)
  return (
    <ToolCardFrame
      kind="updates"
      icon="bell"
      label={copy("tcUpdatesTitle")}
      link={{ href: "#/updates", text: copy("tcOpenUpdates") }}
    >
      {shown.map((item) => {
        const href = safeHref(item.source_url)
        return (
          <div key={item.id} className="ur">
            <span className="tg">{item.doc_type}</span>
            {href ? (
              <a href={href} target="_blank" rel="noopener noreferrer" lang="en">
                {item.title}
              </a>
            ) : (
              <span lang="en">{item.title}</span>
            )}
            <span className="udt">{item.published_at ? shortDate(item.published_at) : ""}</span>
          </div>
        )
      })}
      <CardFoot icon="info" start={fill(copy("tcShown"), { n: shown.length, total })} end={copy("tcFromListing")} />
    </ToolCardFrame>
  )
}

function shortDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "Asia/Karachi" }).format(date)
}
