import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { listUpdates, replayUpdates, type UpdateList } from "../../api/updates"
import type { CopyKey } from "../../i18n"
import { domainLabel } from "../../lib/domains"
import { field, primary, secondary } from "../../ui/styles"

type Copy = (key: CopyKey) => string
const DOMAINS = ["all", "income_tax", "sales_tax", "customs", "corporate_secp", "audit_notice", "property"]

export default function UpdatesPage({ copy }: { copy: Copy }) {
  const [domain, setDomain] = useState("all")
  const [replayError, setReplayError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const query = useQuery({
    queryKey: ["updates", domain],
    queryFn: () => listUpdates(domain),
  })
  const result: UpdateList | null = query.data ?? null
  const error =
    replayError ??
    (query.isError
      ? query.error instanceof Error
        ? query.error.message
        : copy("updatesFailed")
      : null)

  async function replay() {
    setBusy(true)
    setReplayError(null)
    try {
      await replayUpdates()
      await query.refetch()
    } catch (caught) {
      setReplayError(caught instanceof Error ? caught.message : copy("updatesFailed"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h2 className="font-statute text-3xl tracking-tight">{copy("updatesTitle")}</h2>
      <p className="mt-2 max-w-[58ch] text-sm leading-6 text-muted">{copy("updatesHelp")}</p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          {copy("updatesDomain")}
          <select
            className={field}
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
          >
            {DOMAINS.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? copy("updatesAll") : domainLabel(copy, item)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={busy}
          className={secondary}
          onClick={() => void query.refetch()}
        >
          {copy("updatesRefresh")}
        </button>
        <button type="button" disabled={busy} className={primary} onClick={() => void replay()}>
          {copy("updatesReplay")}
        </button>
      </div>
      {(busy || query.isFetching) && !result ? (
        <p className="mt-4 text-sm text-muted">{copy("serviceChecking")}</p>
      ) : null}
      {error ? (
        <p className="mt-3 text-sm text-low" role="alert">
          {error}
        </p>
      ) : null}
      {result ? (
        <div className="mt-6 grid gap-3">
          {result.items.length === 0 ? <p className="text-sm text-muted">{copy("updatesNone")}</p> : null}
          {result.items.map((item) => (
            <article key={item.id} className="rounded-2xl border border-rule bg-field px-5 py-4 text-sm shadow-[0_1px_2px_rgba(26,24,20,0.04)]">
              <h3 className="font-medium">{item.title}</h3>
              <p className="mt-1 text-muted">
                {item.doc_type}
                {item.domain ? `, ${domainLabel(copy, item.domain)}` : ""}
                {item.published_at ? `, ${item.published_at}` : ""}
              </p>
              <p className="mt-2 whitespace-pre-wrap">{item.summary}</p>
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
