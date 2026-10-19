/** Known backend error sentences, in the shell language. */

import type { UiLanguage } from "../lib/session"
import { t, type CopyKey } from "./index"

const KNOWN: Record<string, CopyKey> = {
  "Search failed before an answer could be written.": "searchFailed",
  "The answer took too long.": "answerTooLong",
  "Server error.": "serverError",
  "I can't ignore the rules or reveal a hidden prompt. Ask a tax question and I will answer from the ordinance.":
    "injectionRefusal",
  "I can't help with hiding income, evading tax, or fake documents. For legal filing, use IRIS or call FBR at 051-111-772-772.":
    "evasionRefusal",
}

export function localizedError(message: string, language: UiLanguage): string {
  const key = KNOWN[message]
  if (!key || language !== "roman_urdu") return message
  return t(language, key)
}
