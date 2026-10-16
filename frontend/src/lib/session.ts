export type TaxpayerType = "salaried" | "freelancer" | "business" | "company"
export type FilerStatus = "filer" | "non_filer" | "unknown"
export type Province = "punjab" | "sindh" | "kpk" | "balochistan" | "islamabad" | "gb" | "ajk"
export type UiLanguage = "en" | "roman_urdu"
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
export const CHAT_KEY = "daleelai.chat_id"
export const THEME_KEY = "daleelai.theme"

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
  return created
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
