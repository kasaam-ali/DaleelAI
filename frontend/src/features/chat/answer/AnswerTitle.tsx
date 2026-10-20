/** The question as a serif title, its filing context and time, and the Answer | Sources tabs. */

import type { ReactNode } from "react"
import { splitPlaceholders } from "../../../lib/pii"
import Icon from "../../../shell/icons"
import { Masked } from "../Composer"
import type { Copy } from "./types"

export default function AnswerTitle({
  question,
  redacted = false,
  context,
  when,
  sourceCount,
  sourcesOpen,
  copy,
  onSources,
  onAnswer,
  language,
}: {
  question: string
  /** Personal details were masked before sending: highlight the placeholders and say so. */
  redacted?: boolean
  context: string | null
  when: string | null
  sourceCount: number
  sourcesOpen: boolean
  copy: Copy
  onSources: (opener: HTMLElement) => void
  onAnswer: () => void
  language: ReactNode
}) {
  return (
    <header className="ahead">
      <h2 className="q-title">{redacted ? <Masked parts={splitPlaceholders(question)} /> : question}</h2>
      {redacted ? (
        <p className="redsent">
          <Icon name="lock" size="sm" />
          {copy("redactionSent")}
        </p>
      ) : null}
      {context || when ? (
        <div className="qmeta">
          {context ? (
            <span className="ctx">
              <Icon name="user" size="sm" />
              {context}
            </span>
          ) : null}
          {when ? <span>{when}</span> : null}
        </div>
      ) : null}
      <div className="ans-tabs">
        <button type="button" className={`tb${sourcesOpen ? "" : " on"}`} aria-pressed={!sourcesOpen} onClick={onAnswer}>
          <Icon name="doc" size="sm" />
          {copy("answerTab")}
        </button>
        {sourceCount > 0 ? (
          <button type="button" className={`tb${sourcesOpen ? " on" : ""}`} aria-pressed={sourcesOpen} onClick={(event) => onSources(event.currentTarget)}>
            <Icon name="pdf" size="sm" />
            {copy("sources")}
            <span className="n">{sourceCount}</span>
          </button>
        ) : null}
        <span className="sp" />
        {language}
      </div>
    </header>
  )
}
