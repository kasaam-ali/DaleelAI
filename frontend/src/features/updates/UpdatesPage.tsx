/** FBR updates feed, with a domain filter and a saved replay. */

import { useState } from "react"
import { listUpdates, replayUpdates, summaryFor, type UpdateList } from "../../api/updates"
import type { UiLanguage } from "../../lib/session"
import type { CopyKey } from "../../i18n"

type Copy = (key: CopyKey) => string
const DOMAINS = ["all", "income_tax", "sales_tax", "customs", "corporate_secp", "audit_notice", "property"]

export default function UpdatesPage({ copy, language }: { copy: Copy; language: UiLanguage }) {
  const [domain, setDomain] = useState("all")
  const [result, setResult] = useState<UpdateList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function load(nextDomain = domain) {
    setBusy(true)
    setError(null)
    try {
      setResult(await listUpdates(nextDomain))
    } catch (caught) {
      setResult(null)
      setError(caught instanceof Error ? caught.message : copy("updatesFailed"))
    } finally {
      setBusy(false)
    }
  }

  async function replay() {
    setBusy(true)
    setError(null)
    try {
      await replayUpdates()
      setResult(await listUpdates(domain))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : copy("updatesFailed"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h2 className="page-title">{copy("updatesTitle")}</h2>
      <p className="mt-2 max-w-[48ch] text-muted">{copy("updatesHelp")}</p>
      <div className="panel mt-4 flex flex-wrap items-end gap-3 px-4 py-4">
        <label className="text-sm">
          {copy("updatesDomain")}
          <select
            className="mt-1 min-h-11 border border-rule bg-field px-3 text-base text-ink"
            value={domain}
            onChange={(event) => {
              setDomain(event.target.value)
              void load(event.target.value)
            }}
          >
            {DOMAINS.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? copy("updatesAll") : item}
              </option>
            ))}
          </select>
        </label>
        <button type="button" disabled={busy} className="min-h-11 border border-rule px-3 text-sm" onClick={() => void load()}>
          {copy("updatesRefresh")}
        </button>
        <button type="button" disabled={busy} className="min-h-11 bg-seal px-4 text-paper" onClick={() => void replay()}>
          {copy("updatesReplay")}
        </button>
      </div>
      {error ? <p className="mt-3 text-sm text-low">{error}</p> : null}
      {result ? (
        <div className="mt-6 grid gap-3">
          {result.items.length === 0 ? <p className="text-sm text-muted">{copy("updatesNone")}</p> : null}
          {result.items.map((item) => (
            <article key={item.id} className="border border-rule bg-field px-4 py-4 text-sm">
              <h3 className="font-medium">{item.title}</h3>
              <p className="mt-1 text-muted">
                {item.doc_type}
                {item.domain ? `, ${item.domain}` : ""}
                {item.published_at ? `, ${item.published_at}` : ""}
              </p>
              <p className="mt-2 whitespace-pre-wrap">{summaryFor(item, language)}</p>
              <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block underline">
                {item.source_url}
              </a>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}
