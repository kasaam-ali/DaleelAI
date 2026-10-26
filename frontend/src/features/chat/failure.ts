/** Turns a failed request into the error card, and times the auto-retry. */

export type TurnError = {
  status: number | null
  code: string
  message: string
}

export function asTurnError(err: unknown, fallback: string): TurnError {
  if (err && typeof err === "object") {
    const value = err as { status?: unknown; code?: unknown; message?: unknown }
    const status = typeof value.status === "number" ? value.status : null
    const code = typeof value.code === "string" && value.code ? value.code : "request_failed"
    const message = typeof value.message === "string" && value.message ? value.message : ""
    if (message || status !== null) return { status, code, message: message || fallback }
  }
  if (err instanceof Error && err.message) return { status: null, code: "request_failed", message: err.message }
  return { status: null, code: "request_failed", message: fallback }
}

export function chipLabel(error: TurnError): string {
  if (error.status === 503) return "503 · Providers busy"
  if (error.status === 429) return "429 · Too many requests"
  if (error.status) return `${error.status} · ${error.code}`
  return error.code
}

export function canAutoRetry(error: TurnError): boolean {
  return error.status === 429 || error.status === 503
}

const BACKOFF_MS = [14_000, 30_000, 60_000]

/** 14 s, then 30 s, then 60 s (SPEC §5.2A item 10). After that the card waits for a manual retry. */
export function retryDelayMs(attempt: number): number | null {
  return BACKOFF_MS[attempt] ?? null
}

/** Short request id for the error card footer, e.g. "7f3a·c21e". */
export function shortRequestId(id: string): string {
  const hex = id.replace(/[^0-9a-f]/gi, "").toLowerCase()
  return hex.length >= 8 ? `${hex.slice(0, 4)}·${hex.slice(4, 8)}` : id
}
