/** Loads the updates feed and asks for a saved replay. */

import type { UiLanguage } from "../lib/session"
import { API_URL } from "./client"

export type UpdateItem = {
  id: string
  title: string
  doc_type: string
  domain: string | null
  published_at: string | null
  effective_from: string | null
  summary: string
  summary_en?: string
  summary_ru?: string
  who_is_affected: string | null
  key_changes: string[]
  source_url: string
}

/** English or Roman Urdu half. Prefers the split fields, then the first blank line. */
export function summaryFor(
  item: Pick<UpdateItem, "summary" | "summary_en" | "summary_ru">,
  language: UiLanguage,
): string {
  if (language === "roman_urdu" && item.summary_ru) return item.summary_ru
  if (language === "en" && item.summary_en) return item.summary_en
  const [english, roman] = item.summary.split(/\n\n/, 2)
  if (language === "roman_urdu" && roman) return roman
  return english || item.summary
}

export type UpdateList = {
  items: UpdateItem[]
  page: number
  pages: number
  total: number
}

export async function listUpdates(domain: string): Promise<UpdateList> {
  const params = new URLSearchParams({ domain, limit: "20" })
  const response = await fetch(`${API_URL}/api/v1/updates?${params}`, {
    signal: AbortSignal.timeout(15000),
  })
  const payload = (await response.json()) as UpdateList & { error?: { message?: string } }
  if (!response.ok) throw new Error(payload.error?.message ?? "updates failed")
  return payload
}

export async function replayUpdates(): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/updates/replay`, {
    method: "POST",
    signal: AbortSignal.timeout(60000),
  })
  const payload = (await response.json()) as { error?: { message?: string } }
  if (!response.ok) throw new Error(payload.error?.message ?? "replay failed")
}
