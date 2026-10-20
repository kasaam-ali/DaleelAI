/** Sends a question, streams the answer, and keeps this chat's thread. */

import { useEffect, useRef, useState } from "react"
import {
  getChat,
  sendFeedback,
  streamChat,
  type FeedbackReason,
  type SseEvent,
} from "../../api/chat"
import type { CopyKey } from "../../i18n"
import { localizedError } from "../../i18n/errors"
import { redactPii } from "../../lib/pii"
import {
  asReplyLanguage,
  readAnswerLanguage,
  readCorpusDates,
  readOfflineQueue,
  readSessionId,
  rememberCorpusDate,
  writeAnswerLanguage,
  writeOfflineQueue,
  type AnswerLanguage,
  type ClientTaxYear,
  type Profile,
  type ReplyLanguage,
  type UiLanguage,
} from "../../lib/session"
import AnswerHeader from "./AnswerHeader"
import AnswerSlip, { SourcesRail } from "./AnswerSlip"
import { assistantSnippet } from "./chatText"
import { reduceBucket } from "./bucket"
import Composer from "./Composer"
import NewChat from "./NewChat"
import ErrorCard from "./ErrorCard"
import { asTurnError, canAutoRetry, retryDelayMs } from "./failure"
import { turnsFromHistory } from "./history"
import OfflineBanner from "./OfflineBanner"
import StatusSteps from "./StatusSteps"
import Icon from "../../shell/icons"
import "./states.css"
import { PENDING_PHASES, reducePhases } from "./steps"
import type { Turn } from "./types"
import { useOnline } from "./useOnline"

type Copy = (key: CopyKey) => string

function shownError(message: string | undefined, fallback: string, language: UiLanguage) {
  const text = message?.trim() ?? ""
  if (!text || /json|traceback|exception|routeroutput/i.test(text)) return fallback
  return localizedError(text, language)
}

/** One offline-queue flush per page, even if StrictMode or a remount runs the effect twice. */
const flushLock = { active: false }

export default function ChatPage({
  language,
  profile,
  copy,
  chatId,
  sessionId,
  onChatId,
  onActivity,
  launch = null,
  onLaunchConsumed,
  historyKey = 0,
  taxYear = "TY2027",
  onProfile = () => undefined,
  onTaxYear = () => undefined,
  onSnippet = () => undefined,
}: {
  language: UiLanguage
  profile: Profile
  copy: Copy
  chatId: string | null
  sessionId: string
  onChatId: (chatId: string) => void
  onActivity: () => void
  launch?: { id: string; text: string } | null
  onLaunchConsumed?: () => void
  historyKey?: number
  taxYear?: ClientTaxYear
  onProfile?: (patch: Partial<Profile>) => void
  onTaxYear?: (taxYear: ClientTaxYear) => void
  onSnippet?: (chatId: string, snippet: string) => void
}) {
  const [draft, setDraft] = useState("")
  const [formError, setFormError] = useState<string | null>(null)
  const [queuedItems] = useState(() => readOfflineQueue(localStorage))
  const queueRef = useRef(queuedItems)
  const [bucket, setBucket] = useState<{ id: string | null; turns: Turn[] }>(() => ({
    id: chatId,
    turns: queuedItems.map((item) => blankTurn(item.id, item.text, false, true)),
  }))
  const [busy, setBusy] = useState(false)
  const [away, setAway] = useState(false)
  const [answerLanguage, setAnswerLanguage] = useState<AnswerLanguage>("auto")
  const [queuedCount, setQueuedCount] = useState(queuedItems.length)
  const online = useOnline()
  const answerLanguageRef = useRef<AnswerLanguage>("auto")
  const runRef = useRef(0)
  const retryRef = useRef<{ timer: number | null; attempt: number }>({ timer: null, attempt: 0 })
  const stopRequested = useRef(false)
  const liveTurn = useRef<string | null>(null)
  const scroller = useRef<HTMLDivElement>(null)
  const stick = useRef(true)
  const abortRef = useRef<AbortController | null>(null)
  const born = useRef<string | null>(null)
  const chatIdRef = useRef(chatId)
  chatIdRef.current = chatId
  const busyRef = useRef(busy)
  busyRef.current = busy

  function rememberQueue() {
    writeOfflineQueue(localStorage, queueRef.current)
    setQueuedCount(queueRef.current.length)
  }

  const turns =
    bucket.id === chatId || (born.current !== null && bucket.id === born.current) ? bucket.turns : []

  function setTurns(update: Turn[] | ((current: Turn[]) => Turn[])) {
    setBucket((current) => reduceBucket(current, update, chatIdRef.current, born.current))
  }

  useEffect(
    () => () => {
      abortRef.current?.abort()
      if (retryRef.current.timer != null) window.clearInterval(retryRef.current.timer)
    },
    [],
  )

  useEffect(() => {
    const stored = readAnswerLanguage(localStorage, chatId)
    answerLanguageRef.current = stored
    setAnswerLanguage(stored)
  }, [chatId])

  useEffect(() => {
    if (busy) return
    born.current = null
  }, [busy])

  useEffect(() => {
    if (busyRef.current || !chatId || born.current === chatId) return
    let cancelled = false
    getChat(sessionId, chatId)
      .then((detail) => {
        if (cancelled || born.current === chatId) return
        const snippet = assistantSnippet(detail.messages)
        if (snippet) onSnippetRef.current(chatId, snippet)
        setBucket((current) => {
          const dates = { ...readCorpusDates(localStorage) }
          for (const turn of current.turns) {
            if (turn.messageId && turn.final?.corpus_date) dates[turn.messageId] = turn.final.corpus_date
          }
          return keepLiveTurns(
            current,
            chatId,
            turnsFromHistory(detail.messages, dates),
            queueRef.current,
          )
        })
      })
      .catch(() => {
        if (cancelled || born.current === chatId) return
        setBucket((current) => keepLiveTurns(current, chatId, [], queueRef.current))
      })
    return () => {
      cancelled = true
    }
  }, [chatId, sessionId, historyKey])

  useEffect(() => {
    const element = scroller.current
    const visible = bucket.id === chatId || (born.current !== null && bucket.id === born.current)
    if (!element || !stick.current || !visible) return
    element.scrollTop = element.scrollHeight
  }, [bucket, chatId])

  const [retryTotal, setRetryTotal] = useState<number | null>(null)
  const [announce, setAnnounce] = useState("")
  const preview = redactPii(draft)
  const showPreview = draft.trim().length > 0 && preview !== draft

  function clearRetry() {
    if (retryRef.current.timer != null) {
      window.clearInterval(retryRef.current.timer)
      retryRef.current.timer = null
    }
  }

  function scheduleRetry(id: string, question: string) {
    clearRetry()
    const delay = retryDelayMs(retryRef.current.attempt)
    if (delay == null) return
    let left = Math.round(delay / 1000)
    setRetryTotal(left)
    patch(id, (current) => ({ ...current, autoRetryIn: left }))
    retryRef.current.timer = window.setInterval(() => {
      left -= 1
      if (left > 0) {
        patch(id, (current) => ({ ...current, autoRetryIn: left }))
        return
      }
      clearRetry()
      retryRef.current.attempt += 1
      setAnnounce(copy("autoRetrying"))
      patch(id, (current) => ({ ...current, autoRetryIn: null }))
      void askRef.current(question, { replaceId: id })
    }, 1000)
  }

  async function ask(
    rawText: string,
    options?: { language?: AnswerLanguage; replaceId?: string; flush?: boolean },
  ): Promise<boolean> {
    const raw = rawText.trim()
    if (!raw) {
      setFormError(copy("writeQuestion"))
      return false
    }
    const replacing = Boolean(options?.replaceId)
    if (busyRef.current && !replacing) return false
    const message = redactPii(raw)
    if (message.length > 2000) {
      setFormError(copy("tooLong"))
      return false
    }
    const requested = options?.language ?? answerLanguageRef.current
    setFormError(null)
    stick.current = true
    setAway(false)
    const id = options?.replaceId ?? crypto.randomUUID()
    if (!online && !options?.flush) {
      if (replacing) {
        patch(id, (current) => ({ ...current, queued: true, status: "", error: null, autoRetryIn: null }))
      } else {
        setDraft("")
        setTurns((prev) => [...prev, blankTurn(id, message, message !== raw, true)])
      }
      if (!queueRef.current.some((item) => item.id === id)) queueRef.current.push({ id, text: message })
      rememberQueue()
      return false
    }
    if (!replacing) setDraft("")
    clearRetry()
    if (replacing) {
      patch(id, (current) => ({
        ...current,
        status: options?.flush ? "sending" : "",
        draft: "",
        sources: [],
        phases: [...PENDING_PHASES],
        phaseTimes: [null, null, null, null],
        sentAt: Date.now(),
        queued: false,
        stopped: false,
        autoRetryIn: null,
        autoRetryCancelled: false,
        final: null,
        error: null,
        toolCard: null,
        toolNote: false,
      }))
    } else {
      setTurns((prev) => [...prev, { ...blankTurn(id, message, message !== raw, false), sentAt: Date.now() }])
    }
    const run = ++runRef.current
    const live = () => runRef.current === run
    stopRequested.current = false
    liveTurn.current = id
    abortRef.current?.abort()
    setBusy(true)
    const controller = new AbortController()
    abortRef.current = controller
    try {
      await streamChat(
        {
          chat_id: chatIdRef.current,
          message,
          language: requested,
          tax_year: taxYear,
          profile,
          client_request_id: id,
        },
        readSessionId(localStorage),
        (event) => {
          if (live()) applyEvent(id, event)
        },
        controller.signal,
      )
      if (!live()) return false
      queueRef.current = queueRef.current.filter((item) => item.id !== id)
      rememberQueue()
      return true
    } catch (err) {
      if (!live()) return false
      const held = Boolean(options?.flush) && !stopRequested.current
      if (!controller.signal.aborted) {
        const error = asTurnError(err, copy("answerFailed"))
        const messageText = shownError(error.message, copy("answerFailed"), language)
        if (held && !queueRef.current.some((item) => item.id === id)) {
          queueRef.current.push({ id, text: message })
          rememberQueue()
        }
        patch(id, (current) => ({
          ...current,
          status: "",
          queued: held,
          error: { ...error, message: held ? copy("queueHeld") : messageText },
        }))
        if (!held && canAutoRetry(error)) scheduleRetry(id, message)
      } else if (held) {
        if (!queueRef.current.some((item) => item.id === id)) queueRef.current.push({ id, text: message })
        rememberQueue()
        patch(id, (current) => ({
          ...current,
          status: "",
          queued: true,
          stopped: false,
          error: { status: null, code: "queued", message: copy("queueHeld") },
        }))
      } else {
        patch(id, (current) => ({
          ...current,
          status: "",
          stopped: stopRequested.current || current.stopped,
        }))
      }
      return false
    } finally {
      if (live()) setBusy(false)
    }
  }

  const onSnippetRef = useRef(onSnippet)
  onSnippetRef.current = onSnippet

  function shownAnswerLanguage(turn: Turn, last: boolean): ReplyLanguage | null {
    if (turn.replyLanguage) return turn.replyLanguage
    if (last && answerLanguage !== "auto") return answerLanguage
    return turn.detectedLanguage
  }

  function chooseAnswerLanguage(next: ReplyLanguage, turn: Turn) {
    const last = turns[turns.length - 1]?.id === turn.id
    const active =
      turn.replyLanguage ??
      (last && answerLanguageRef.current !== "auto" ? answerLanguageRef.current : turn.detectedLanguage)
    if (next === active) return
    answerLanguageRef.current = next
    setAnswerLanguage(next)
    const openChat = chatIdRef.current
    if (openChat) writeAnswerLanguage(localStorage, openChat, next)
    patch(turn.id, (current) => ({ ...current, replyLanguage: next }))
    void ask(turn.question, { language: next, replaceId: turn.id })
  }

  const askRef = useRef(ask)
  const consumeLaunchRef = useRef(onLaunchConsumed)
  const launched = useRef<string | null>(null)
  useEffect(() => {
    askRef.current = ask
    consumeLaunchRef.current = onLaunchConsumed
  })
  useEffect(() => {
    if (!launch || launched.current === launch.id) return
    launched.current = launch.id
    const timer = window.setTimeout(() => consumeLaunchRef.current?.(), 0)
    void askRef.current(launch.text)
    return () => window.clearTimeout(timer)
  }, [launch])

  useEffect(() => {
    if (!online) return
    // Deferred so React StrictMode's mount/unmount/mount cannot start and then abort a send.
    // One flush at a time; queued questions go out in order, each with its own client_request_id.
    let cancelled = false
    void Promise.resolve().then(() => {
      if (cancelled || flushLock.active) return
      flushLock.active = true
      void (async () => {
        try {
          while (queueRef.current.length > 0) {
            const item = queueRef.current[0]
            const ok = await askRef.current(item.text, { replaceId: item.id, flush: true })
            if (!ok || queueRef.current[0]?.id === item.id) return
          }
        } finally {
          flushLock.active = false
        }
      })()
    })
    return () => {
      cancelled = true
    }
  }, [online])

  function applyEvent(id: string, event: SseEvent) {
    if (event.event === "meta") {
      born.current = event.data.chat_id
      // The next queued question must go to this chat even before the parent re-renders.
      chatIdRef.current = event.data.chat_id
      setBucket((current) => ({ id: event.data.chat_id, turns: current.turns }))
      onActivity()
      const detected = asReplyLanguage(event.data.language)
      if (answerLanguageRef.current !== "auto") {
        writeAnswerLanguage(localStorage, event.data.chat_id, answerLanguageRef.current)
      }
      onChatId(event.data.chat_id)
      patch(id, (current) => ({
        ...current,
        messageId: event.data.message_id,
        taxYear: event.data.tax_year,
        intent: event.data.intent,
        detectedLanguage: detected ?? current.detectedLanguage,
      }))
    } else if (event.event === "step") {
      patch(id, (current) => ({
        ...current,
        status: "",
        ...phaseUpdate(current, event.data.node, event.data.status),
      }))
    } else if (event.event === "token") {
      patch(id, (current) => ({ ...current, draft: current.draft + event.data.text, status: "" }))
    } else if (event.event === "sources") {
      patch(id, (current) => ({ ...current, sources: event.data.sources }))
    } else if (event.event === "final") {
      if (born.current) onSnippetRef.current(born.current, event.data.answer)
      patch(id, (current) => {
        if (current.messageId && event.data.corpus_date) {
          rememberCorpusDate(localStorage, current.messageId, event.data.corpus_date)
        }
        return {
          ...current,
          final: event.data,
          draft: event.data.answer,
          taxYear: event.data.tax_year,
          status: "",
        }
      })
    } else if (event.event === "error") {
      patch(id, (current) => ({
        ...current,
        status: "",
        error: {
          status: null,
          code: event.data.code,
          message: shownError(event.data.message, copy("answerFailed"), language),
        },
      }))
    } else if (event.event === "tool_result") {
      patch(id, (current) => ({ ...current, toolCard: event.data.card }))
    } else if (event.event === "done") {
      patch(id, (current) => ({ ...current, status: "" }))
    }
  }

  function patch(id: string, update: (turn: Turn) => Turn) {
    setTurns((prev) => prev.map((turn) => (turn.id === id ? update(turn) : turn)))
  }

  async function onFeedback(id: string, messageId: string, rating: "up" | "down", reason: FeedbackReason | null) {
    patch(id, (current) => ({ ...current, feedback: rating, feedbackNote: null }))
    try {
      await sendFeedback(readSessionId(localStorage), messageId, rating, reason)
      patch(id, (current) => ({ ...current, feedback: rating, feedbackNote: copy("feedbackSaved") }))
    } catch {
      patch(id, (current) => ({
        ...current,
        feedback: reason ? current.feedback : null,
        feedbackNote: copy("feedbackFailed"),
      }))
    }
  }

  function onScroll() {
    const element = scroller.current
    if (!element) return
    const near = element.scrollHeight - element.scrollTop - element.clientHeight < 80
    stick.current = near
    setAway(!near)
  }

  function resume() {
    stick.current = true
    setAway(false)
    const element = scroller.current
    if (element) element.scrollTop = element.scrollHeight
  }

  function stop() {
    stopRequested.current = true
    const id = liveTurn.current
    abortRef.current?.abort()
    if (id) patch(id, (current) => ({ ...current, status: "", stopped: true }))
    setBusy(false)
  }

  function retryNow(turn: Turn) {
    clearRetry()
    retryRef.current.attempt = 0
    void ask(turn.question, { replaceId: turn.id })
  }

  function cancelAutoRetry(id: string) {
    clearRetry()
    patch(id, (current) => ({ ...current, autoRetryIn: null, autoRetryCancelled: true }))
  }

  async function copyQuestion(question: string) {
    try {
      await navigator.clipboard.writeText(question)
    } catch {
      /* clipboard can be unavailable */
    }
  }

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {online ? null : <OfflineBanner queuedCount={queuedCount} copy={copy} />}
      <p className="sr-only" aria-live="polite" data-retry-announce>
        {announce}
      </p>
      <div ref={scroller} onScroll={onScroll} className="min-h-0 flex-1 overflow-y-auto" aria-live="polite">
        <div
          className="mx-auto flex w-full max-w-5xl flex-col px-4 py-8"
        >
          {turns.length === 0 ? (
            <NewChat
              copy={copy}
              profile={profile}
              taxYear={taxYear}
              draft={draft}
              busy={busy}
              error={formError}
              preview={showPreview ? preview : null}
              onDraft={(value) => {
                setDraft(value)
                setFormError(null)
              }}
              onSubmit={() => void ask(draft)}
              onStop={stop}
              onProfile={onProfile}
              onTaxYear={onTaxYear}
              onPick={(question) => void ask(question)}
            />
          ) : (
            turns.map((turn) => {
              const streaming = Boolean(turn.draft) || turn.sources.length > 0
              return (
              <div
                key={turn.id}
                className="rise-in mt-6 w-full xl:grid xl:grid-cols-[minmax(0,1fr)_17rem] xl:items-start xl:gap-x-10"
              >
                <div className="min-w-0 xl:col-start-1 xl:row-start-1">
                  <div className="flex justify-end">
                    <p
                      className={
                        turn.queued
                          ? "qbubble max-w-[min(85%,40rem)] whitespace-pre-wrap text-ink"
                          : "max-w-[min(85%,40rem)] border-l-2 border-seal py-1 pl-3 whitespace-pre-wrap text-ink"
                      }
                    >
                      {turn.question}
                    </p>
                  </div>
                  {turn.redacted ? <p className="mt-1 text-right text-sm text-muted">{copy("redactionSent")}</p> : null}
                    {turn.queued ? (
                      <p className="qstate" data-queued>
                        <Icon name="wifiOff" size="sm" />
                        {copy("queued")}
                      </p>
                    ) : null}
                    {turn.queued && turn.error ? (
                      <p className="mt-1 text-right text-sm text-muted">{turn.error.message}</p>
                    ) : null}
                </div>
                {turn.queued ? null : (
                <div className="mt-4 flex min-w-0 gap-3 xl:col-start-1 xl:row-start-2">
                  <span className="mt-1 inline-flex h-8 w-8 shrink-0 items-center justify-center bg-seal text-seal-ink" aria-hidden="true">
                    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.6">
                      <path d="M6 5.5h7.2L17 9.2V18.5H6v-13z" strokeLinejoin="round" />
                      <path d="M13 5.5V9h4" strokeLinejoin="round" />
                    </svg>
                  </span>
                  <div className="min-w-0 flex-1">
                    <AnswerHeader
                      detected={turn.detectedLanguage}
                      selected={shownAnswerLanguage(turn, turn.id === turns[turns.length - 1]?.id)}
                      copy={copy}
                      onSelect={(next) => chooseAnswerLanguage(next, turn)}
                    />
                    {turn.status === "sending" ? <p className="text-sm text-muted">{copy("queueSending")}</p> : null}
                    {showSteps(turn) ? (
                      <StatusSteps phases={turn.phases} times={turn.phaseTimes} copy={copy} skeleton={!streaming} />
                    ) : null}
                    {turn.stopped && !turn.final && !turn.error ? (
                      <div data-motion-slot="stopped" role="status" className="border border-rule bg-field px-4 py-4">
                        <h3 className="font-statute text-lg font-medium">{copy("stoppedTitle")}</h3>
                        <p className="mt-2 text-sm text-muted">{copy("stoppedDetail")}</p>
                        <button
                          type="button"
                          onClick={() => retryNow(turn)}
                          className="mt-4 min-h-11 bg-seal px-4 text-sm font-medium text-seal-ink"
                        >
                          {copy("retry")}
                        </button>
                      </div>
                    ) : null}
                    {turn.error ? (
                      <ErrorCard
                        error={turn.error}
                        secondsLeft={turn.autoRetryIn}
                        totalSeconds={retryTotal}
                        cancelled={turn.autoRetryCancelled}
                        requestId={turn.id}
                        copy={copy}
                        onRetry={() => retryNow(turn)}
                        onCopy={() => void copyQuestion(turn.question)}
                        onCancel={() => cancelAutoRetry(turn.id)}
                      />
                    ) : null}
                    {!turn.queued && !turn.error && !turn.stopped && (streaming || !showSteps(turn)) ? (
                      <AnswerSlip
                        turn={turn}
                        language={language}
                        copy={copy}
                        onAsk={(question) => void ask(question)}
                        onFeedback={(rating, reason) => {
                          if (turn.messageId) void onFeedback(turn.id, turn.messageId, rating, reason)
                        }}
                      />
                    ) : null}
                  </div>
                </div>
                )}
                <SourcesRail
                  turn={turn}
                  language={language}
                  copy={copy}
                  className="xl:col-start-2 xl:row-start-2 xl:mt-4"
                />
              </div>
              )
            })
          )}
        </div>
      </div>
      {turns.length > 0 && away ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-28 flex justify-center">
          <button
            type="button"
            onClick={resume}
            className="pointer-events-auto min-h-11 rounded-full border border-rule bg-field px-4 text-sm shadow-sm"
          >
            {copy("resumeScroll")}
          </button>
        </div>
      ) : null}
      {turns.length > 0 ? (
        <Composer
          value={draft}
          busy={busy}
          error={formError}
          preview={showPreview ? preview : null}
          copy={copy}
          onChange={(value) => {
            setDraft(value)
            setFormError(null)
          }}
          onSubmit={() => void ask(draft)}
          onStop={stop}
          muted={!online}
        />
      ) : null}
    </div>
  )
}

function phaseUpdate(turn: Turn, node: string, status: "start" | "end"): Pick<Turn, "phases" | "phaseTimes"> {
  const phases = reducePhases(turn.phases, node, status)
  const elapsed = turn.sentAt == null ? null : Math.max(0, Date.now() - turn.sentAt) / 1000
  const phaseTimes = phases.map((phase, index) =>
    phase === "done" && turn.phases[index] !== "done" ? elapsed : (turn.phaseTimes[index] ?? null),
  )
  return { phases, phaseTimes }
}

function showSteps(turn: Turn): boolean {
  if (turn.queued || turn.error || turn.stopped || turn.final || turn.toolCard) return false
  if (turn.draft || turn.sources.length > 0) return turn.phases[3] !== "done"
  return true
}

function blankTurn(id: string, question: string, redacted: boolean, queued: boolean): Turn {
  return {
    id,
    question,
    redacted,
    status: "",
    draft: "",
    sources: [],
    intent: null,
    detectedLanguage: null,
    phases: [...PENDING_PHASES],
    queued,
    stopped: false,
    replyLanguage: null,
    autoRetryIn: null,
    autoRetryCancelled: false,
    sentAt: null,
    phaseTimes: [null, null, null, null],
    final: null,
    error: null,
    messageId: null,
    taxYear: null,
    feedback: null,
    feedbackNote: null,
    toolNote: false,
    toolCard: null,
  }
}

function keepLiveTurns(
  current: { id: string | null; turns: Turn[] },
  chatId: string,
  loaded: Turn[],
  queued: { id: string; text: string }[],
): { id: string | null; turns: Turn[] } {
  const live = current.id === chatId || current.id === null
  const currentHasAnswer = current.turns.some((turn) => turn.draft || turn.final || turn.status || turn.error)
  const loadedHasAnswer = loaded.some((turn) => turn.draft || turn.final)
  const base =
    live && currentHasAnswer && !loadedHasAnswer
      ? current.turns
      : live && current.turns.length > 0 && loaded.length === 0
        ? current.turns
        : loaded
  return { id: chatId, turns: mergeQueued(base, queued) }
}

function mergeQueued(turns: Turn[], queued: { id: string; text: string }[]): Turn[] {
  const ids = new Set(turns.map((turn) => turn.id))
  const extra = queued
    .filter((item) => !ids.has(item.id))
    .map((item) => blankTurn(item.id, item.text, false, true))
  return extra.length === 0 ? turns : [...turns, ...extra]
}
