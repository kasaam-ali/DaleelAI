/** Saves the anonymous session, profile, language, and theme in the browser. */

export type TaxpayerType = "salaried" | "freelancer" | "business" | "company"
export type FilerStatus = "filer" | "non_filer" | "unknown"
export type Province = "punjab" | "sindh" | "kpk" | "balochistan" | "islamabad" | "gb" | "ajk"
export type UiLanguage = "en" | "roman_urdu"
export type AnswerLanguage = "auto" | "en" | "roman_urdu"
export type ReplyLanguage = Exclude<AnswerLanguage, "auto">
export type Theme = "light" | "dark"

export type Profile = {
  taxpayer_type: TaxpayerType | null
  filer_status: FilerStatus | null
  province: Province | null
}

export const EMPTY_PROFILE: Profile = {
  taxpayer_type: null,
  filer_status: null,
  province: null,
}

export const SESSION_KEY = "daleelai.session_id"
export const PROFILE_KEY = "daleelai.profile"
export const LANGUAGE_KEY = "daleelai.language"
export const ANSWER_LANGUAGE_KEY = "daleelai.answer_language"
export const OFFLINE_QUEUE_KEY = "daleelai.offline_queue"
export const CHAT_KEY = "daleelai.chat_id"
export const THEME_KEY = "daleelai.theme"
export const CORPUS_DATES_KEY = "daleelai.corpus_dates"
export const TAX_YEAR_KEY = "daleelai.tax_year"

export type QueuedQuestion = { id: string; text: string }
export type ClientTaxYear = "TY2026" | "TY2027"

export type StorageLike = {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

const TAXPAYER = new Set<TaxpayerType>(["salaried", "freelancer", "business", "company"])
const FILER = new Set<FilerStatus>(["filer", "non_filer", "unknown"])
const PROVINCE = new Set<Province>([
  "punjab",
  "sindh",
  "kpk",
  "balochistan",
  "islamabad",
  "gb",
  "ajk",
])

function oneOf<T extends string>(value: unknown, allowed: Set<T>): T | null {
  return typeof value === "string" && allowed.has(value as T) ? (value as T) : null
}

export function sanitizeProfile(value: unknown): Profile {
  if (!value || typeof value !== "object") return { ...EMPTY_PROFILE }
  const raw = value as Record<string, unknown>
  return {
    taxpayer_type: oneOf(raw.taxpayer_type, TAXPAYER),
    filer_status: oneOf(raw.filer_status, FILER),
    province: oneOf(raw.province, PROVINCE),
  }
}

export function readSessionId(storage: StorageLike): string {
  const existing = storage.getItem(SESSION_KEY)
  if (existing) return existing
  const created = crypto.randomUUID()
  storage.setItem(SESSION_KEY, created)
  return created
}

export function clearLocalHistory(storage: StorageLike): string {
  const created = crypto.randomUUID()
  storage.setItem(SESSION_KEY, created)
  storage.removeItem(CHAT_KEY)
  storage.removeItem(CORPUS_DATES_KEY)
  return created
}

/** Deletes the session on the server, then rotates the local id. A failed delete keeps the id. */
export async function clearStoredHistory(
  storage: StorageLike,
  sessionId: string,
  remove: (sessionId: string) => Promise<void>,
): Promise<string> {
  await remove(sessionId)
  return clearLocalHistory(storage)
}

export function readCorpusDates(storage: StorageLike): Record<string, string> {
  const raw = storage.getItem(CORPUS_DATES_KEY)
  if (!raw) return {}
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== "object") return {}
    const dates: Record<string, string> = {}
    for (const [id, value] of Object.entries(parsed)) {
      if (typeof value === "string" && value.trim()) dates[id] = value
    }
    return dates
  } catch {
    return {}
  }
}

export function rememberCorpusDate(storage: StorageLike, messageId: string, date: string) {
  const when = date.trim()
  if (!messageId || !when) return
  const dates = readCorpusDates(storage)
  if (dates[messageId] === when) return
  dates[messageId] = when
  storage.setItem(CORPUS_DATES_KEY, JSON.stringify(dates))
}

export function readProfile(storage: StorageLike): Profile {
  const raw = storage.getItem(PROFILE_KEY)
  if (!raw) return { ...EMPTY_PROFILE }
  try {
    return sanitizeProfile(JSON.parse(raw))
  } catch {
    return { ...EMPTY_PROFILE }
  }
}

export function writeProfile(storage: StorageLike, profile: Profile): void {
  storage.setItem(PROFILE_KEY, JSON.stringify(sanitizeProfile(profile)))
}

export function readLanguage(storage: StorageLike): UiLanguage {
  return storage.getItem(LANGUAGE_KEY) === "roman_urdu" ? "roman_urdu" : "en"
}

export function writeLanguage(storage: StorageLike, language: UiLanguage): void {
  storage.setItem(LANGUAGE_KEY, language)
}

export function readChatId(storage: StorageLike): string | null {
  return storage.getItem(CHAT_KEY)
}

export function writeChatId(storage: StorageLike, chatId: string): void {
  storage.setItem(CHAT_KEY, chatId)
}

export function profilePayload(profile: Profile): Profile {
  return sanitizeProfile(profile)
}

const ANSWER_LANGUAGES = new Set<AnswerLanguage>(["auto", "en", "roman_urdu"])

export function asReplyLanguage(value: string | null | undefined): ReplyLanguage | null {
  return value === "en" || value === "roman_urdu" ? value : null
}

export function readAnswerLanguage(storage: StorageLike, chatId: string | null): AnswerLanguage {
  if (!chatId) return "auto"
  const raw = storage.getItem(ANSWER_LANGUAGE_KEY)
  if (!raw) return "auto"
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>
    const value = parsed[chatId]
    return typeof value === "string" && ANSWER_LANGUAGES.has(value as AnswerLanguage)
      ? (value as AnswerLanguage)
      : "auto"
  } catch {
    return "auto"
  }
}

export function writeAnswerLanguage(storage: StorageLike, chatId: string, language: AnswerLanguage): void {
  let parsed: Record<string, string> = {}
  const raw = storage.getItem(ANSWER_LANGUAGE_KEY)
  if (raw) {
    try {
      const value = JSON.parse(raw) as unknown
      if (value && typeof value === "object") parsed = value as Record<string, string>
    } catch {
      parsed = {}
    }
  }
  parsed[chatId] = language
  storage.setItem(ANSWER_LANGUAGE_KEY, JSON.stringify(parsed))
}

export function readOfflineQueue(storage: StorageLike): QueuedQuestion[] {
  const raw = storage.getItem(OFFLINE_QUEUE_KEY)
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed.flatMap((item) => {
      if (!item || typeof item !== "object") return []
      const row = item as Record<string, unknown>
      if (typeof row.id !== "string" || typeof row.text !== "string" || !row.text.trim()) return []
      return [{ id: row.id, text: row.text }]
    })
  } catch {
    return []
  }
}

export function writeOfflineQueue(storage: StorageLike, items: QueuedQuestion[]): void {
  if (items.length === 0) {
    storage.removeItem(OFFLINE_QUEUE_KEY)
    return
  }
  storage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(items))
}

function karachiYearMonth(now: Date): { year: number; month: number } {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Karachi",
    year: "numeric",
    month: "numeric",
  }).formatToParts(now)
  const read = (type: string) => Number(parts.find((part) => part.type === type)?.value ?? "0")
  return { year: read("year"), month: read("month") }
}

/** Pakistan's tax year ends on 30 June. TY2027 is 1 Jul 2026 through 30 Jun 2027. */
export function currentTaxYear(now = new Date()): ClientTaxYear {
  const { year, month } = karachiYearMonth(now)
  const ending = month >= 7 ? year + 1 : year
  return ending <= 2026 ? "TY2026" : "TY2027"
}

export function readTaxYear(storage: StorageLike, now = new Date()): ClientTaxYear {
  const stored = storage.getItem(TAX_YEAR_KEY)
  if (stored === "TY2026" || stored === "TY2027") return stored
  return currentTaxYear(now)
}

export function writeTaxYear(storage: StorageLike, taxYear: ClientTaxYear): void {
  storage.setItem(TAX_YEAR_KEY, taxYear)
}
