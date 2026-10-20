/** One of the three Home tool cards: tilt, glare, depth layers, and art that plays once then loops on hover. */

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react"
import Icon, { type IconName } from "../../shell/icons"
import { useTilt } from "./useTilt"

export type ToolArt = "ask" | "calc" | "notice"

export const INTRO_MS = 3400

function Art({ kind, question, estimated }: { kind: ToolArt; question: string; estimated: string }) {
  if (kind === "ask")
    return (
      <>
        <div className="bub q">{question}</div>
        <div className="bub a">
          <span className="l" />
          <span className="l" />
          <span className="l" />
          Section 1XX<span className="c">1</span>
        </div>
        <div className="src-float">
          <span>s.1XX</span>
          <span>Div. X</span>
          <span>s.1YY</span>
        </div>
      </>
    )
  if (kind === "calc")
    return (
      <>
        <div className="calc-tag">
          {estimated}
          <b>Rs 24,000</b>
        </div>
        <div className="bars">
          <i style={{ height: "38%" }} />
          <i style={{ height: "56%" }} />
          <i className="k" style={{ height: "92%" }} />
          <i style={{ height: "64%" }} />
          <i style={{ height: "46%" }} />
        </div>
      </>
    )
  return (
    <>
      <div className="doc">
        <div className="h" />
        <div className="ln" />
        <div className="ln" style={{ width: "80%" }} />
        <div className="ln" style={{ opacity: 0 }} />
        <div className="ln" />
        <div className="ln" style={{ width: "65%" }} />
        <div className="ln" />
        <div className="ln" style={{ width: "40%" }} />
        <span className="mark2" />
      </div>
      <span className="lens" />
    </>
  )
}

export default function ToolCard({
  title,
  description,
  meta,
  action,
  icon,
  art,
  feature = false,
  badge,
  index,
  question,
  estimated,
  onLaunch,
}: {
  title: string
  description: string
  meta: string
  action: string
  icon: IconName
  art: ToolArt
  feature?: boolean
  badge?: ReactNode
  index: number
  question: string
  estimated: string
  onLaunch: (card: HTMLElement) => void
}) {
  const cardRef = useRef<HTMLDivElement>(null)
  const innerRef = useRef<HTMLDivElement>(null)
  const [intro, setIntro] = useState(true)
  useTilt(cardRef, innerRef)

  useEffect(() => {
    const timer = window.setTimeout(() => setIntro(false), INTRO_MS)
    return () => window.clearTimeout(timer)
  }, [])

  return (
    <div
      ref={cardRef}
      role="link"
      tabIndex={0}
      data-tilt
      data-reveal
      data-art={art}
      style={{ "--i": index } as CSSProperties}
      className={`tcard${feature ? " feature" : ""}${intro ? " intro" : ""}`}
      onClick={() => cardRef.current && onLaunch(cardRef.current)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault()
          if (cardRef.current) onLaunch(cardRef.current)
        }
      }}
    >
      <div ref={innerRef} className="tc-inner">
        <div className="art" aria-hidden="true">
          <Art kind={art} question={question} estimated={estimated} />
        </div>
        <div className="tc-body">
          <b>
            <Icon name={icon} size="sm" />
            {title}
            {badge ? <small>{badge}</small> : null}
          </b>
          <p>{description}</p>
        </div>
        <div className="tc-foot">
          <span>{meta}</span>
          <span className="go">
            {action}
            <Icon name="chev" size="sm" />
          </span>
        </div>
        <span className="tc-glare" />
      </div>
    </div>
  )
}
