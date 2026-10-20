/**
 * The source panel (right column on desktop, bottom sheet on phones) and its law view
 * (split view on desktop, full screen on phones). SPEC §5.2A items 5–6.
 */

import { useEffect, useRef } from "react"
import type { Source } from "../../../api/chat"
import Icon from "../../../shell/icons"
import {
  copyReference,
  docShort,
  fill,
  formatDate,
  fullRef,
  pdfHref,
  sectionRef,
  siteOf,
} from "./refs"
import { safeHref } from "../../../lib/safeUrl"
import { panelId, type Copy } from "./types"

export default function SourcePanel({
  turnId,
  sources,
  n,
  law,
  taxYear,
  lawDate,
  copy,
  onSelect,
  onLaw,
  onBack,
  onClose,
  onCopied,
}: {
  turnId: string
  sources: Source[]
  n: number
  law: boolean
  taxYear: string | null
  lawDate: string | null
  copy: Copy
  onSelect: (n: number) => void
  onLaw: (n: number) => void
  onBack: () => void
  onClose: () => void
  onCopied: (message: string) => void
}) {
  const heading = useRef<HTMLHeadingElement>(null)
  const source = sources[n - 1]

  useEffect(() => {
    heading.current?.focus({ preventScroll: true })
  }, [n, law])

  if (!source) return null
  const web = source.library === "web"
  const pdf = web ? null : pdfHref(source)
  const page = web ? safeHref(source.url) : null
  const library = sources.map((item, index) => ({ item, n: index + 1 })).filter(({ item }) => item.library !== "web")

  async function copyRef() {
    try {
      await navigator.clipboard.writeText(copyReference(source, taxYear))
      onCopied(copy("refCopied"))
    } catch {
      onCopied(copy("shareFailed"))
    }
  }

  const actions = (
    <>
      {pdf ? (
        <a className="primary" href={pdf} target="_blank" rel="noopener noreferrer">
          <Icon name="pdf" size="sm" />
          {source.page != null ? fill(copy("openPdfPage"), { page: source.page }) : copy("openPdfNoPage")}
          <span className="sr-only"> {copy("opensOfficial")}</span>
        </a>
      ) : null}
      {page ? (
        <a className="primary" href={page} target="_blank" rel="noopener noreferrer">
          <Icon name="globe" size="sm" />
          {siteOf(source)}
          <span className="sr-only"> {copy("opensOfficial")}</span>
        </a>
      ) : null}
      <button type="button" className="ghost" onClick={() => void copyRef()}>
        <Icon name="copy" size="sm" />
        {copy("copyRef")}
      </button>
    </>
  )

  const close = (
    <button type="button" className="iconbtn" onClick={onClose} aria-label={copy("closeLabel")}>
      <Icon name="close" size="sm" />
    </button>
  )

  if (law && !web) {
    return (
      <aside
        id={panelId(turnId)}
        className="panel-c card lawmode"
        aria-label={copy("lawViewTitle")}
        data-law-view
      >
        <div className="pc-head">
          <button type="button" className="linkbtn" onClick={onBack}>
            <Icon name="chev" size="sm" className="back" />
            {copy("sources")}
          </button>
          <h2 ref={heading} tabIndex={-1} className="lv-title">
            {copy("lawViewTitle")}
          </h2>
          {close}
        </div>
        <div className="lv-scroll">
          <div className="doc-tabs" dir="ltr">
            {library.map(({ item, n: number }) => (
              <button
                key={number}
                type="button"
                className={`dt${number === n ? " on" : ""}`}
                aria-pressed={number === n}
                onClick={() => onLaw(number)}
              >
                <span className="tag">{number}</span>
                {sectionRef(item)}
              </button>
            ))}
          </div>
          <div className="doc-head">
            <p className="k" dir="ltr">
              {source.title}
              {source.page != null ? ` · ${copy("pageShort")}${source.page}` : ""}
            </p>
            <h3 dir="ltr">{source.section ? `Section ${source.section}` : docShort(source)}</h3>
          </div>
          <div className="lawtext" dir="ltr" lang="en">
            <p>
              <mark>{source.snippet}</mark>
            </p>
          </div>
          <p className="hl-note">
            <Icon name="info" size="sm" />
            {copy("highlightedNote")}
          </p>
        </div>
        <div className="lv-foot">{actions}</div>
      </aside>
    )
  }

  return (
    <aside id={panelId(turnId)} className="panel-c card" aria-label={copy("sources")} data-source-panel>
      <span className="grab" aria-hidden="true" />
      <div className="pc-head">
        <h2 ref={heading} tabIndex={-1}>
          {copy("sources")}
        </h2>
        <div className="pc-tabs">
          {sources.map((item, index) => (
            <button
              key={index}
              type="button"
              className={`cite${index + 1 === n ? " on" : ""}`}
              aria-pressed={index + 1 === n}
              aria-label={fill(copy("sourceChipName"), { n: index + 1, ref: fullRef(item) })}
              onClick={() => onSelect(index + 1)}
            >
              {index + 1}
            </button>
          ))}
        </div>
        {close}
      </div>
      <div className="pc-body">
        <p className="pc-ref" dir="ltr">
          {fullRef(source)}
        </p>
        <p className="pc-sub">{source.title}</p>
        {web ? (
          <p className="pc-meta web">{fill(copy("checkedOn"), { date: formatDate(source.fetched_at) })}</p>
        ) : (
          <p className="pc-meta">
            {[
              source.page != null ? `${copy("pageShort")}${source.page}` : "",
              taxYear ? fill(copy("metaLine"), { year: taxYear.replace(/^TY/, ""), date: formatDate(lawDate) }) : "",
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        )}
        {source.snippet ? (
          <>
            <p className="pc-lbl">{web ? source.title : copy("lawTextLabel")}</p>
            <blockquote className="quote" dir="ltr" lang="en">
              {source.snippet}
            </blockquote>
          </>
        ) : null}
        <div className="pc-actions">{actions}</div>
        {!web ? (
          <button type="button" className="linkbtn mt-2" onClick={() => onLaw(n)}>
            <Icon name="doc" size="sm" />
            {copy("openLawView")}
          </button>
        ) : null}
      </div>
    </aside>
  )
}
