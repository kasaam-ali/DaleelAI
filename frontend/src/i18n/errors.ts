/** Known backend error sentences, in the shell language. */

import type { UiLanguage } from "../lib/session"
import { t, type CopyKey } from "./index"

const KNOWN: Record<string, CopyKey> = {
  "Search failed before an answer could be written.": "searchFailed",
  "The answer took too long.": "answerTooLong",
}

export function localizedError(message: string, language: UiLanguage): string {
  const key = KNOWN[message]
  if (!key || language !== "roman_urdu") return message
  return t(language, key)
}
