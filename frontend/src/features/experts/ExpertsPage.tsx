/** Asks a question and lists matching public experts for a city. */

import { useEffect, useRef, useState } from "react"
import { findExperts, type ExpertFind } from "../../api/experts"
import type { CopyKey } from "../../i18n"
import type { UiLanguage } from "../../lib/session"

type Copy = (key: CopyKey) => string
const inputClass = "mt-1 min-h-11 w-full border border-rule bg-field px-3 text-base text-ink"
const CITIES = ["", "Karachi", "Lahore", "Islamabad"]

export default function ExpertsPage({
  copy,
  language,
  initialQuery = "",
  initialCategory = null,
}: {
  copy: Copy
  language: UiLanguage
  initialQuery?: string
  initialCategory?: string | null
}) {
  const [query, setQuery] = useState(initialQuery)
  const [city, setCity] = useState("")
  const [category, setCategory] = useState<string | null>(initialCategory)
  const [result, setResult] = useState<ExpertFind | null>(null)
  const [error, setError] = useState<string | null>(null)
  const handoffReady = Boolean(initialQuery.trim() && initialCategory)
  const [busy, setBusy] = useState(handoffReady)
  const copyRef = useRef(copy)
  const handoff = `${initialQuery}\0${initialCategory ?? ""}`
  const [appliedHandoff, setAppliedHandoff] = useState("")
  if (initialQuery.trim() && initialCategory && handoff !== appliedHandoff) {
    setAppliedHandoff(handoff)
    setQuery(initialQuery)
    setCategory(initialCategory)
  }

  useEffect(() => {
    copyRef.current = copy
  }, [copy])

  useEffect(() => {
    if (!initialQuery.trim() || !initialCategory) return
    let active = true
    findExperts(initialQuery.trim(), "", initialCategory)
      .then((next) => {
        if (active) setResult(next)
      })
      .catch((caught) => {
        if (!active) return
        setResult(null)
        setError(caught instanceof Error ? caught.message : copyRef.current("expertsFailed"))
      })
      .finally(() => {
        if (active) setBusy(false)
      })
    return () => {
      active = false
    }
  }, [initialQuery, initialCategory])

  async function search(nextCategory: string | null) {
    if (!query.trim()) return
    setBusy(true)
    setError(null)
    setCategory(nextCategory)
    try {
      setResult(await findExperts(query.trim(), city, nextCategory))
    } catch (caught) {
      setResult(null)
      setError(caught instanceof Error ? caught.message : copy("expertsFailed"))
    } finally {
      setBusy(false)
    }
  }

  const roman = language === "roman_urdu"

  return (
    <section>
      <h2 className="page-title">{copy("expertsTitle")}</h2>
      <p className="mt-2 max-w-[48ch] text-muted">{copy("expertsHelp")}</p>
      <form
        className="panel mt-4 grid gap-3 px-4 py-4"
        onSubmit={(event) => {
          event.preventDefault()
          void search(category)
        }}
      >
        <label className="text-sm">
          {copy("expertsQuery")}
          <textarea className={inputClass} value={query} rows={3} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <label className="text-sm">
          {copy("expertsCity")}
          <select className={inputClass} value={city} onChange={(event) => setCity(event.target.value)}>
            {CITIES.map((item) => (
              <option key={item || "any"} value={item}>
                {item || copy("expertsAnyCity")}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={busy} className="min-h-11 bg-seal px-4 text-paper">
          {copy("expertsFind")}
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-low">{error}</p> : null}
      {result ? (
        <div className="mt-6 border border-rule bg-field px-4 py-4">
          <p>{language === "roman_urdu" && result.advice_ru ? result.advice_ru : result.advice}</p>
          {result.classification.low_confidence ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {["income_tax", "sales_tax", "customs", "corporate_secp", "audit_notice", "property"].map(
                (item) => (
                  <button
                    key={item}
                    type="button"
                    className="min-h-11 border border-rule px-3 text-sm"
                    onClick={() => void search(item)}
                  >
                    {categoryLabel(item, copy)}
                  </button>
                ),
              )}
            </div>
          ) : null}
          {result.experts.length === 0 ? <p className="mt-3 text-sm text-muted">{copy("expertsNone")}</p> : null}
          <ul className="mt-3 grid gap-3">
            {result.experts.map((expert) => (
              <li key={expert.id} className="border border-rule px-3 py-3 text-sm">
                <p className="font-medium">
                  {expert.name}
                  {expert.firm ? `, ${expert.firm}` : ""}
                </p>
                <p className="text-muted">
                  {expert.city}. {expert.specialties.map((item) => categoryLabel(item, copy)).join(", ")}
                </p>
                <p className="text-muted">
                  {expert.source}. {expert.last_updated}
                </p>
                <a href={expert.profile_url} target="_blank" rel="noopener noreferrer" className="underline">
                  {expert.profile_url}
                </a>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm">
            {roman && result.disclaimer_ru ? result.disclaimer_ru : result.disclaimer}
          </p>
          <p className="mt-1 text-sm text-muted">
            {roman && result.removal_contact_ru ? result.removal_contact_ru : result.removal_contact}
          </p>
        </div>
      ) : null}
    </section>
  )
}

const CATEGORY_KEYS: Record<string, CopyKey> = {
  income_tax: "category_income_tax",
  sales_tax: "category_sales_tax",
  customs: "category_customs",
  corporate_secp: "category_corporate_secp",
  audit_notice: "category_audit_notice",
  property: "category_property",
}

/** Human label for a category key such as income_tax; unknown keys fall back to readable text. */
export function categoryLabel(key: string, copy: Copy): string {
  const known = CATEGORY_KEYS[key]
  return known ? copy(known) : key.replace(/_/g, " ")
}
