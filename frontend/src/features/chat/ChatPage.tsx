/** Sends a question, streams the answer, and keeps this chat's thread. */

import { useEffect, useRef, useState } from "react"
import {
  getChat,
  sendFeedback,
  streamChat,
  type FeedbackReason,
  type FinalData,
  type SseEvent,
  type StoredMessage,
} from "../../api/chat"
import type { CopyKey } from "../../i18n"
import { localizedError } from "../../i18n/errors"
import { redactPii } from "../../lib/pii"
import {
  asReplyLanguage,
  readAnswerLanguage,
  readSessionId,
  writeAnswerLanguage,
  type AnswerLanguage,
  type Profile,
  type ReplyLanguage,
  type UiLanguage,
} from "../../lib/session"
import AnswerHeader from "./AnswerHeader"
import AnswerSlip from "./AnswerSlip"
import { reduceBucket } from "./bucket"
import Composer from "./Composer"
import EmptyState from "./EmptyState"
import ErrorCard from "./ErrorCard"
import { asTurnError, canAutoRetry, retryDelayMs } from "./failure"
import OfflineBanner from "./OfflineBanner"
import StatusSteps from "./StatusSteps"
import { PENDING_PHASES, reducePhases } from "./steps"
import type { Turn } from "./types"
import { useOnline } from "./useOnline"

type Copy = (key: CopyKey) => string

function shownError(message: string | undefined, fallback: string, language: UiLanguage) {
  const text = message?.trim() ?? ""
  if (!text || /json|traceback|exception|routeroutput/i.test(text)) return fallback
  return localizedError(text, language)
}

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
}) {
  const [draft, setDraft] = useState("")
  const [formError, setFormError] = useState<string | null>(null)
  const [bucket, setBucket] = useState<{ id: string | null; turns: Turn[] }>({ id: chatId, turns: [] })
  const [busy, setBusy] = useState(false)
  const [away, setAway] = useState(false)
  const [answerLanguage, setAnswerLanguage] = useState<AnswerLanguage>("auto")
  const [queuedCount, setQueuedCount] = useState(0)
  const online = useOnline()
  const answerLanguageRef = useRef<AnswerLanguage>("auto")
  const runRef = useRef(0)
  const queueRef = useRef<{ id: string; text: string }[]>([])
  const retryRef = useRef<{ timer: number | null; attempt: number }>({ timer: null, attempt: 0 })
  const scroller = useRef<HTMLDivElement>(null)
  const stick = useRef(true)
  const abortRef = useRef<AbortController | null>(null)
  const born = useRef<string | null>(null)
  const chatIdRef = useRef(chatId)
  chatIdRef.current = chatId
  const busyRef = useRef(busy)
  busyRef.current = busy
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
        const loaded = turnsFromHistory(detail.messages)
        setBucket((current) => keepLiveTurns(current, chatId, loaded))
      })
      .catch(() => {
        if (cancelled || born.current === chatId) return
        setBucket((current) => keepLiveTurns(current, chatId, []))
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
    patch(id, (current) => ({ ...current, autoRetryIn: left }))
    retryRef.current.timer = window.setInterval(() => {
      left -= 1
      if (left > 0) {
        patch(id, (current) => ({ ...current, autoRetryIn: left }))
        return
      }
      clearRetry()
      retryRef.current.attempt += 1
      patch(id, (current) => ({ ...current, autoRetryIn: null }))
      void askRef.current(question, { replaceId: id })
    }, 1000)
  }

  async function ask(
    rawText: string,
    options?: { language?: AnswerLanguage; replaceId?: string; flush?: boolean },
  ) {
    const raw = rawText.trim()
    if (!raw) {
      setFormError(copy("writeQuestion"))
      return
    }
    const replacing = Boolean(options?.replaceId)
    if (busyRef.current && !replacing) return
    const message = redactPii(raw)
    if (message.length > 2000) {
      setFormError(copy("tooLong"))
      return
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
      setQueuedCount(queueRef.current.length)
      return
    }
    if (!replacing) setDraft("")
    clearRetry()
    if (replacing) {
      patch(id, (current) => ({
        ...current,
        status: "",
        draft: "",
        sources: [],
        phases: [...PENDING_PHASES],
        queued: false,
        autoRetryIn: null,
        final: null,
        error: null,
        toolCard: null,
        toolNote: false,
      }))
    } else {
      setTurns((prev) => [...prev, blankTurn(id, message, message !== raw, false)])
    }
    const run = ++runRef.current
    const live = () => runRef.current === run
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
          tax_year: null,
          profile,
        },
        readSessionId(localStorage),
        (event) => {
          if (live()) applyEvent(id, event)
        },
        controller.signal,
      )
    } catch (err) {
      if (!live()) return
      if (!controller.signal.aborted) {
        const error = asTurnError(err, copy("answerFailed"))
        const messageText = shownError(error.message, copy("answerFailed"), language)
        patch(id, (current) => ({ ...current, status: "", error: { ...error, message: messageText } }))
        if (canAutoRetry(error)) scheduleRetry(id, message)
      } else {
        patch(id, (current) => ({ ...current, status: "" }))
      }
    } finally {
      if (live()) setBusy(false)
    }
  }

  function chooseAnswerLanguage(next: ReplyLanguage, turn: Turn) {
    const active = answerLanguageRef.current === "auto" ? turn.detectedLanguage : answerLanguageRef.current
    if (next === active) return
    answerLanguageRef.current = next
    setAnswerLanguage(next)
    const openChat = chatIdRef.current
    if (openChat) writeAnswerLanguage(localStorage, openChat, next)
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
    const pending = queueRef.current.splice(0)
    if (pending.length === 0) return
    setQueuedCount(0)
    let stopped = false
    void (async () => {
      for (const item of pending) {
        if (stopped) return
        await askRef.current(item.text, { replaceId: item.id, flush: true })
      }
    })()
    return () => {
      stopped = true
    }
  }, [online])

  function applyEvent(id: string, event: SseEvent) {
    if (event.event === "meta") {
      born.current = event.data.chat_id
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
        phases: reducePhases(current.phases, event.data.node, event.data.status),
      }))
    } else if (event.event === "token") {
      patch(id, (current) => ({ ...current, draft: current.draft + event.data.text, status: "" }))
    } else if (event.event === "sources") {
      patch(id, (current) => ({ ...current, sources: event.data.sources }))
    } else if (event.event === "final") {
      patch(id, (current) => ({
        ...current,
        final: event.data,
        draft: event.data.answer,
        taxYear: event.data.tax_year,
        status: "",
      }))
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
    abortRef.current?.abort()
    setBusy(false)
  }

  function retryNow(turn: Turn) {
    clearRetry()
    retryRef.current.attempt = 0
    void ask(turn.question, { replaceId: turn.id })
  }

  function cancelAutoRetry(id: string) {
    clearRetry()
    patch(id, (current) => ({ ...current, autoRetryIn: null }))
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
      <div ref={scroller} onScroll={onScroll} className="min-h-0 flex-1 overflow-y-auto" aria-live="polite">
        <div
          className="mx-auto flex w-full max-w-5xl flex-col px-4 py-8"
        >
          {turns.length === 0 ? (
            <EmptyState copy={copy} />
          ) : (
            turns.map((turn) => (
              <div key={turn.id} className="rise-in mt-6">
                <div className="flex justify-end">
                  <p className="max-w-[min(85%,40rem)] border-l-2 border-seal py-1 pl-3 whitespace-pre-wrap text-ink">
                    {turn.question}
                  </p>
                </div>
                {turn.redacted ? <p className="mt-1 text-right text-sm text-muted">{copy("redactionSent")}</p> : null}
                <div className="mt-4 flex gap-3">
                  <span className="mt-1 inline-flex h-8 w-8 shrink-0 items-center justify-center bg-seal text-seal-ink" aria-hidden="true">
                    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.6">
                      <path d="M6 5.5h7.2L17 9.2V18.5H6v-13z" strokeLinejoin="round" />
                      <path d="M13 5.5V9h4" strokeLinejoin="round" />
                    </svg>
                  </span>
                  <div className="min-w-0 flex-1">
                    {turn.id === turns[turns.length - 1]?.id ? (
                      <AnswerHeader
                        detected={turn.detectedLanguage}
                        selected={answerLanguage === "auto" ? turn.detectedLanguage : answerLanguage}
                        copy={copy}
                        onSelect={(next) => chooseAnswerLanguage(next, turn)}
                      />
                    ) : null}
                    {turn.queued ? <p className="text-sm text-muted">{copy("queued")}</p> : null}
                    {showSteps(turn) ? <StatusSteps phases={turn.phases} copy={copy} /> : null}
                    {turn.error ? (
                      <ErrorCard
                        error={turn.error}
                        secondsLeft={turn.autoRetryIn}
                        copy={copy}
                        onRetry={() => retryNow(turn)}
                        onCopy={() => void copyQuestion(turn.question)}
                        onCancel={() => cancelAutoRetry(turn.id)}
                      />
                    ) : null}
                    {!turn.queued && !turn.error && !showSteps(turn) ? (
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
              </div>
            ))
          )}
        </div>
      </div>
      {away ? (
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
    </div>
  )
}

function showSteps(turn: Turn): boolean {
  return !turn.queued && !turn.error && !turn.final && !turn.draft && turn.sources.length === 0 && !turn.toolCard
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
    autoRetryIn: null,
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
): { id: string | null; turns: Turn[] } {
  const live = current.id === chatId || current.id === null
  const currentHasAnswer = current.turns.some((turn) => turn.draft || turn.final || turn.status || turn.error)
  const loadedHasAnswer = loaded.some((turn) => turn.draft || turn.final)
  if (live && currentHasAnswer && !loadedHasAnswer) return { id: chatId, turns: current.turns }
  if (live && current.turns.length > 0 && loaded.length === 0) return { id: chatId, turns: current.turns }
  return { id: chatId, turns: loaded }
}

function turnsFromHistory(messages: StoredMessage[]): Turn[] {
  const turns: Turn[] = []
  let question: StoredMessage | null = null
  for (const message of messages) {
    if (message.role === "user") {
      if (question) turns.push(historyTurn(question, null))
      question = message
    } else if (question) {
      turns.push(historyTurn(question, message))
      question = null
    }
  }
  if (question) turns.push(historyTurn(question, null))
  return turns
}

function historyTurn(question: StoredMessage, answer: StoredMessage | null): Turn {
  const source = answer?.answer_source
  const confidence = answer?.confidence
  const final: FinalData | null =
    answer && (source === "verified" || source === "web" || source === "none")
      ? {
          answer: answer.content,
          answer_source: source,
          confidence: confidence === "high" || confidence === "low" ? confidence : "medium",
          verified: Boolean(answer.verified),
          model: answer.model ?? "",
          tax_year: answer.tax_year ?? "",
          corpus_date: "",
          action_links: [],
          follow_ups: [],
          cached: false,
          trace: answer.intent
            ? {
                intent: answer.intent,
                search_query: "",
                retrieved: null,
                rerank_top: null,
                verified: answer.verified,
                latency_ms: null,
              }
            : null,
        }
      : null
  return {
    id: question.id,
    question: question.content,
    redacted: false,
    status: "",
    draft: answer?.content ?? "",
    sources: answer?.sources ?? [],
    intent: answer?.intent ?? null,
    detectedLanguage: asReplyLanguage(answer?.language ?? question.language),
    phases: [...PENDING_PHASES],
    queued: false,
    autoRetryIn: null,
    final,
    error: null,
    messageId: answer?.id ?? null,
    taxYear: answer?.tax_year ?? null,
    feedback: answer?.feedback ?? null,
    feedbackNote: null,
    toolNote: false,
    toolCard: null,
  }
}
