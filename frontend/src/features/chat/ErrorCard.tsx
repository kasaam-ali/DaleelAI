/** Failed answer (SPEC §5.2A item 10, §6): code chip, plain reason, the real backend message, Retry now, Copy question,
 *  and for 429/503 an auto-retry countdown with a visible Cancel. */

import type { CopyKey } from "../../i18n"
import Icon from "../../shell/icons"
import { chipLabel, shortRequestId, type TurnError } from "./failure"

type Copy = (key: CopyKey) => string

const RING = 57

export default function ErrorCard({
  error,
  secondsLeft,
  totalSeconds,
  cancelled = false,
  requestId,
  copy,
  onRetry,
  onCopy,
  onCancel,
}: {
  error: TurnError
  secondsLeft: number | null
  totalSeconds?: number | null
  cancelled?: boolean
  requestId?: string | null
  copy: Copy
  onRetry: () => void
  onCopy: () => void
  onCancel: () => void
}) {
  const plain = error.status === 503 ? copy("errPlain503") : null
  const share = secondsLeft != null && totalSeconds ? secondsLeft / totalSeconds : 1
  return (
    <div data-motion-slot="error-card" role="alert" className="card ecard">
      <div className="rhead">
        <span className="ri">
          <Icon name="alert" />
        </span>
        <div>
          <span className="code2" data-error-code>
            {chipLabel(error)}
          </span>
          <h3>{copy("answerFailedTitle")}</h3>
          {plain ? <p>{plain}</p> : null}
          <p className="realmsg" dir="ltr">
            {error.message}
          </p>
        </div>
      </div>
      <div className="rsec">
        <div className="retryrow">
          <button type="button" className="btnp" onClick={onRetry}>
            <Icon name="refresh" size="sm" />
            {copy("retryNow")}
          </button>
          <button type="button" className="btng" onClick={onCopy}>
            <Icon name="copy" size="sm" />
            {copy("copyQuestion")}
          </button>
          {secondsLeft != null ? (
            <>
              <span className="cd">
                <svg viewBox="0 0 22 22" aria-hidden="true">
                  <circle cx="11" cy="11" r="9" fill="none" stroke="var(--rule)" strokeWidth="2.5" />
                  <circle
                    className="p"
                    cx="11"
                    cy="11"
                    r="9"
                    fill="none"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    style={{ strokeDasharray: RING, strokeDashoffset: RING * (1 - share) }}
                  />
                </svg>
                <span role="timer" aria-live="off">
                  {copy("autoRetryIn").replace("{n}", String(secondsLeft))}
                </span>
              </span>
              <button type="button" className="btng sm" data-cancel-auto-retry onClick={onCancel}>
                <Icon name="close" size="sm" />
                {copy("cancelAutoRetry")}
              </button>
            </>
          ) : cancelled ? (
            <span className="cd" data-auto-retry-off>
              <Icon name="info" size="sm" />
              {copy("autoRetryOff")}
            </span>
          ) : null}
        </div>
        <p className="emeta">
          <Icon name="checkShield" size="sm" />
          {copy("questionSaved")}
          {requestId ? ` ${copy("requestId")} ${shortRequestId(requestId)}` : ""}
        </p>
      </div>
    </div>
  )
}
