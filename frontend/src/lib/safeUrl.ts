export function safeHref(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    if (url.protocol === "http:" || url.protocol === "https:") return url.href
  } catch {
    return null
  }
  return null
}
