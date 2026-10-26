/** Amount checks and the message shown when the tax service cannot be reached. */

export function wholeRupees(raw: string): number | null {
  const cleaned = raw.replace(/,/g, "").trim()
  if (!/^\d+$/.test(cleaned)) return null
  const value = Number(cleaned)
  return Number.isSafeInteger(value) ? value : null
}

export function mapCalcError(
  err: unknown,
  unreachable: string,
  fallback: string,
): { message: string; retry: boolean } {
  const reason = err instanceof Error ? err.message.trim() : ""
  const name = err instanceof Error ? err.name : ""
  const network =
    err instanceof TypeError ||
    name === "AbortError" ||
    name === "TimeoutError" ||
    /failed to fetch|networkerror|load failed|timed out|timeout/i.test(`${name} ${reason}`)
  if (!network) return { message: reason || fallback, retry: false }
  const why = reason || name || "network error"
  console.error(`Calculator request failed: ${why}`)
  return { message: unreachable, retry: true }
}
