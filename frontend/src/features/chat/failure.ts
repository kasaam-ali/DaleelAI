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

/** 20s, then 40s, then 80s. After that the card waits for a manual retry. */
export function retryDelayMs(attempt: number): number | null {
  if (attempt < 0 || attempt >= 3) return null
  return 20_000 * 2 ** attempt
}
