/** Copy (with sources), Share, Helpful / Not helpful, and the reason form after Not helpful. */

import { useState } from "react"
import type { FeedbackReason } from "../../../api/chat"
import Icon from "../../../shell/icons"
import type { CopyKey } from "../../../i18n"
import type { Copy } from "./types"

/** Mockup reason chips and the API reason each one sends. */
const REASONS: { key: CopyKey; reason: FeedbackReason }[] = [
  { key: "fbWrongSection", reason: "wrong" },
  { key: "fbOutdated", reason: "outdated" },
  { key: "fbHard", reason: "other" },
  { key: "fbNotAnswered", reason: "incomplete" },
  { key: "fbOther", reason: "other" },
]

export default function AnswerActions({
  copyText,
  canRate,
  feedback,
  feedbackNote,
  copy,
  onToast,
  onFeedback,
}: {
  copyText: string
  canRate: boolean
  feedback: "up" | "down" | null
  feedbackNote: string | null
  copy: Copy
  onToast: (message: string) => void
  onFeedback: (rating: "up" | "down", reason: FeedbackReason | null, comment: string | null) => void
}) {
  const [formOpen, setFormOpen] = useState(false)
  const [picked, setPicked] = useState(0)
  const [note, setNote] = useState("")

  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(copyText)
      onToast(copy("copiedWithSources"))
    } catch {
      onToast(copy("shareFailed"))
    }
  }

  async function share() {
    const url = window.location.href
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title: "DaleelAI", text: copyText, url })
      } catch {
        /* the person closed the share sheet */
      }
      return
    }
    try {
      await navigator.clipboard.writeText(url)
      onToast(copy("answerLinkCopied"))
    } catch {
      onToast(copy("shareFailed"))
    }
  }

  const sent = feedback !== null && !formOpen
  return (
    <>
      <div className="acts">
        <button type="button" className="ab" onClick={() => void copyAnswer()}>
          <Icon name="copy" size="sm" />
          {copy("copyShort")}
        </button>
        <button type="button" className="ab" onClick={() => void share()}>
          <Icon name="share" size="sm" />
          {copy("shareShort")}
        </button>
        <span className="flex-1" />
        {canRate ? (
          <>
            <button
              type="button"
              className={`ab${feedback === "up" ? " on" : ""}`}
              aria-pressed={feedback === "up"}
              aria-label={copy("helpful")}
              disabled={feedback !== null}
              onClick={() => onFeedback("up", null, null)}
            >
              <Icon name="up" size="sm" />
              {copy("helpful")}
            </button>
            <button
              type="button"
              className={`ab dn${feedback === "down" || formOpen ? " on" : ""}`}
              aria-pressed={feedback === "down" || formOpen}
              aria-label={copy("notHelpful")}
              aria-expanded={formOpen}
              disabled={feedback !== null}
              onClick={() => setFormOpen(true)}
            >
              <Icon name="down" size="sm" />
            </button>
          </>
        ) : null}
      </div>
      {formOpen ? (
        <div className="card fbcard" role="group" aria-label={copy("whatWasWrong")}>
          <b>{copy("whatWasWrong")}</b>
          <div className="fbchips">
            {REASONS.map((item, index) => (
              <button
                key={item.key}
                type="button"
                className={index === picked ? "on" : ""}
                aria-pressed={index === picked}
                onClick={() => setPicked(index)}
              >
                {copy(item.key)}
              </button>
            ))}
          </div>
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder={copy("fbPlaceholder")}
            aria-label={copy("fbPlaceholder")}
            maxLength={1000}
          />
          <div className="row2">
            <span className="inline-flex items-center gap-1.5">
              <Icon name="lock" size="sm" />
              {copy("fbPrivacy")}
            </span>
            <button
              type="button"
              className="btnp"
              onClick={() => {
                setFormOpen(false)
                onFeedback("down", REASONS[picked].reason, note.trim() || null)
              }}
            >
              {copy("fbSend")}
            </button>
          </div>
        </div>
      ) : null}
      {sent && feedbackNote ? (
        <p className="fbthanks meta" role="status">
          <Icon name="check" size="sm" />
          {feedbackNote}
        </p>
      ) : null}
    </>
  )
}
