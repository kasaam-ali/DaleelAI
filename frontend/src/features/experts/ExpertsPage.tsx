import { useEffect, useRef, useState } from "react"
import { findExperts, type ExpertFind } from "../../api/experts"
import type { CopyKey } from "../../i18n"
import { domainLabel } from "../../lib/domains"
import { field, primary, secondary } from "../../ui/styles"

type Copy = (key: CopyKey) => string
const inputClass = field
const CITIES = ["", "Karachi", "Lahore", "Islamabad"]

export default function ExpertsPage({
  copy,
  initialQuery = "",
  initialCategory = null,
}: {
  copy: Copy
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
    if (!query.trim()) {
      setError(copy("expertsNeedQuery"))
      return
    }
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

  return (
    <section>
      <h2 className="font-statute text-3xl tracking-tight">{copy("expertsTitle")}</h2>
      <p className="mt-2 max-w-[58ch] text-sm leading-6 text-muted">{copy("expertsHelp")}</p>
      <form
        className="mt-4 grid gap-3"
        onSubmit={(event) => {
          event.preventDefault()
          void search(null)
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
        <button type="submit" disabled={busy} className={`${primary} w-full sm:w-auto`}>
          {copy("expertsFind")}
        </button>
      </form>
      {category ? <p className="mt-3 text-sm text-muted">{domainLabel(copy, category)}</p> : null}
      {error ? (
        <p className="mt-3 text-sm text-low" role="alert">
          {error}
        </p>
      ) : null}
      {result ? (
        <div className="mt-6 rounded-2xl border border-rule bg-field px-5 py-5 shadow-[0_1px_2px_rgba(26,24,20,0.04),0_18px_40px_rgba(26,24,20,0.05)]">
          <p>{result.advice}</p>
          {result.classification.low_confidence ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {["income_tax", "sales_tax", "customs", "corporate_secp", "audit_notice", "property"].map(
                (item) => (
                  <button
                    key={item}
                    type="button"
                    className={secondary}
                    onClick={() => void search(item)}
                  >
                    {domainLabel(copy, item)}
                  </button>
                ),
              )}
            </div>
          ) : null}
          {result.experts.length === 0 ? <p className="mt-3 text-sm text-muted">{copy("expertsNone")}</p> : null}
          <ul className="mt-3 grid gap-3">
            {result.experts.map((expert) => (
              <li key={expert.id} className="rounded-xl border border-rule bg-paper px-3 py-3 text-sm">
                <p className="font-medium">
                  {expert.name}
                  {expert.firm ? `, ${expert.firm}` : ""}
                </p>
                <p className="text-muted">
                  {expert.city}. {expert.specialties.join(", ")}
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
          <p className="mt-4 text-sm">{result.disclaimer}</p>
          <p className="mt-1 text-sm text-muted">{result.removal_contact}</p>
        </div>
      ) : null}
    </section>
  )
}
