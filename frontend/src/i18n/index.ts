/** Returns the English or Roman Urdu string for a key. */

import en from "./en.json" with { type: "json" }
import romanUrdu from "./roman_urdu.json" with { type: "json" }
import type { UiLanguage } from "../lib/session"

export type CopyKey = keyof typeof en

const copy = {
  en,
  roman_urdu: romanUrdu,
} satisfies Record<UiLanguage, typeof en>

export function t(language: UiLanguage, key: CopyKey): string {
  return copy[language][key]
}
