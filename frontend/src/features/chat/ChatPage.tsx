import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react"
import { sendFeedback, streamChat, type FeedbackReason, type SseEvent } from "../../api/chat"
import type { CopyKey } from "../../i18n"
import { redactPii } from "../../lib/pii"
import { readChatId, readSessionId, writeChatId, type Profile, type UiLanguage } from "../../lib/session"
import AnswerSlip from "./AnswerSlip"
import type { Turn } from "./types"

type Copy = (key: CopyKey) => string

const STEPS: Record<string, CopyKey> = {
  rewrite: "stepRewrite",
  retrieve: "stepRetrieve",
  rerank: "stepRerank",
  expand: "stepExpand",
  sufficiency: "stepSufficiency",
  web_fallback: "stepWeb",
  generate: "stepGenerate",
  verify: "stepVerify",
  links: "stepLinks",
}

export default function ChatPage({
  language,
  profile,
  copy,
}: {
  language: UiLanguage
  profile: Profile
  copy: Copy
}) {
  const [draft, setDraft] = useState("")
  const [formError, setFormError] = useState<string | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState(false)
  const chatId = useRef<string | null>(null)
  const chatLoaded = useRef(false)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  function currentChatId(): string | null {
    if (!chatLoaded.current) {
      chatLoaded.current = true
      chatId.current = readChatId(localStorage)
    }
    return chatId.current
  }

  const preview = redactPii(draft)
  const showPreview = draft.trim().length > 0 && preview !== draft

  async function ask(rawText: string) {
    const raw = rawText.trim()
    if (!raw) {
      setFormError(copy("writeQuestion"))
      return
    }
    if (busy) return
    const message = redactPii(raw)
    if (message.length > 2000) {
      setFormError(copy("tooLong"))
      return
    }
    setFormError(null)
    setDraft("")
    const id = crypto.randomUUID()
    const turn: Turn = {
      id,
      question: message,
      redacted: message !== raw,
      status: copy("stepWorking"),
      draft: "",
      sources: [],
      intent: null,
      final: null,
      error: null,
      messageId: null,
      taxYear: null,
      feedback: null,
      feedbackNote: null,
      toolNote: false,
      toolCard: null,
    }
    setTurns((prev) => [...prev, turn])
    setBusy(true)
    const controller = new AbortController()
    abortRef.current = controller
    try {
      await streamChat(
        {
          chat_id: currentChatId(),
          message,
          language,
          tax_year: null,
          profile,
        },
        readSessionId(localStorage),
        (event) => applyEvent(id, event),
        controller.signal,
      )
    } catch {
      if (!controller.signal.aborted) {
        patch(id, (current) => ({
          ...current,
          status: "",
          error: current.error ?? copy("answerFailed"),
        }))
      }
    } finally {
      setBusy(false)
    }
  }

  function applyEvent(id: string, event: SseEvent) {
    if (event.event === "meta") {
      chatId.current = event.data.chat_id
      writeChatId(localStorage, event.data.chat_id)
      patch(id, (current) => ({
        ...current,
        messageId: event.data.message_id,
        taxYear: event.data.tax_year,
        intent: event.data.intent,
      }))
    } else if (event.event === "step" && event.data.status === "start") {
      patch(id, (current) => ({ ...current, status: copy(STEPS[event.data.node] ?? "stepWorking") }))
    } else if (event.event === "step") {
      patch(id, (current) => ({ ...current, status: "" }))
    } else if (event.event === "token") {
      patch(id, (current) => ({ ...current, draft: current.draft + event.data.text }))
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
        error: event.data.message || copy("answerFailed"),
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

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    void ask(draft)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      void ask(draft)
    }
  }

  return (
    <div className="mt-8">
      {turns.map((turn) => (
        <AnswerSlip
          key={turn.id}
          turn={turn}
          language={language}
          copy={copy}
          onAsk={(question) => void ask(question)}
          onFeedback={(rating, reason) => {
            if (turn.messageId) void onFeedback(turn.id, turn.messageId, rating, reason)
          }}
        />
      ))}

      <form id="ask" onSubmit={onSubmit} className="sticky bottom-0 mt-8 border-t border-rule bg-paper py-4">
        <label htmlFor="question" className="block text-sm font-medium">
          {copy("questionLabel")}
        </label>
        <textarea
          id="question"
          value={draft}
          maxLength={2000}
          onChange={(event) => {
            setDraft(event.target.value)
            setFormError(null)
          }}
          onKeyDown={onKeyDown}
          placeholder={copy("placeholder")}
          className="mt-2 min-h-24 w-full border border-rule bg-field px-3 py-3 text-base text-ink"
        />
        <p className="mt-2 text-sm text-muted">{copy("enterHint")}</p>
        {showPreview ? (
          <p className="mt-2 max-w-[68ch] text-sm">
            {copy("redactionPreview")} {preview}
          </p>
        ) : null}
        {formError ? (
          <p className="mt-2 text-sm text-low" role="alert">
            {formError}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={busy}
          className="mt-3 min-h-11 bg-seal px-4 text-sm font-medium text-seal-ink transition-opacity duration-150 hover:opacity-90 active:opacity-80 disabled:bg-rule disabled:text-muted"
        >
          {busy ? copy("asking") : copy("ask")}
        </button>
      </form>
    </div>
  )
}
