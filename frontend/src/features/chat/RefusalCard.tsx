/** A limit of the library, not a failed request. */

import type { ActionLink } from "../../api/chat"
import type { CopyKey } from "../../i18n"
import { safeHref } from "../../lib/safeUrl"
import type { RefusalKind } from "./refusal"

type Copy = (key: CopyKey) => string

const ACCENT: Record<RefusalKind, string> = {
  evidence: "var(--muted)",
  scope: "var(--seal)",
  declined: "var(--low)",
  provincial: "var(--warning)",
}

const CHIP_CLASS: Record<RefusalKind, string> = {
  evidence: "bg-elevated text-muted",
  scope: "bg-mint text-seal",
  declined: "bg-elevated text-low",
  provincial: "bg-elevated text-warning",
}

const TITLE: Record<RefusalKind, CopyKey> = {
  evidence: "refusalEvidenceTitle",
  scope: "refusalScopeTitle",
  declined: "refusalDeclinedTitle",
  provincial: "refusalProvincialTitle",
}

const LABEL: Record<RefusalKind, CopyKey> = {
  evidence: "refusalEvidenceKind",
  scope: "refusalScopeKind",
  declined: "refusalDeclinedKind",
  provincial: "refusalProvincialKind",
}

const TRY: Record<RefusalKind, CopyKey> = {
  evidence: "refusalTry",
  scope: "refusalScopeTry",
  declined: "refusalDeclinedTry",
  provincial: "refusalProvincialTry",
}

const FALLBACK: Record<RefusalKind, CopyKey[]> = {
  evidence: ["suggestCapital", "suggestYear", "suggestBusiness"],
  scope: ["starterFreelance", "starterSalary", "starterNotice"],
  declined: ["suggestDeductions", "suggestZakat", "suggestPension"],
  provincial: ["suggestRestaurant", "suggestGoodsTax"],
}

export default function RefusalCard({
  kind,
  reason,
  authority,
  query,
  retrieved,
  suggestions,
  links,
  copy,
  onAsk,
}: {
  kind: RefusalKind
  reason: string
  authority: string | null
  query: string | null
  retrieved: number | null
  suggestions: string[]
  links: ActionLink[]
  copy: Copy
  onAsk: (question: string) => void
}) {
  const chips = suggestions.length > 0 ? suggestions : FALLBACK[kind].map((key) => copy(key))
  const official = links.filter((link) => safeHref(link.url))
  const title =
    kind === "provincial" && authority ? `${copy("handledBy")} ${authority}` : copy(TITLE[kind])
  return (
    <div
      data-motion-slot="refusal-card"
      className="border border-rule bg-field"
      style={{ borderInlineStartWidth: 4, borderInlineStartColor: ACCENT[kind] }}
    >
      <div className="px-4 py-4">
        <p className={`inline-block px-2 py-1 text-xs font-medium ${CHIP_CLASS[kind]}`}>{copy(LABEL[kind])}</p>
        <h3 className="mt-3 font-statute text-xl font-medium">{title}</h3>
        <p className="mt-2 max-w-[62ch] text-sm">{reason}</p>
      </div>
      <div className="border-t border-rule px-4 py-3">
        <h4 className="text-sm font-medium text-muted">{copy(TRY[kind])}</h4>
        <div className="mt-2 flex flex-wrap gap-2">
          {chips.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => onAsk(question)}
              className="min-h-11 border border-rule bg-paper px-3 text-start text-sm"
            >
              {question}
            </button>
          ))}
        </div>
      </div>
      {kind === "evidence" || kind === "declined" || official.length > 0 ? (
        <div className="border-t border-rule px-4 py-3">
          <h4 className="text-sm font-medium text-muted">{copy("refusalOfficial")}</h4>
          {kind === "evidence" || kind === "declined" ? (
            <p className="mt-2 text-sm">
              {copy("helpline")} · {copy("helplineDetail")}
            </p>
          ) : null}
          <ul className="mt-2 grid gap-2">
            {(kind === "evidence" ? [{ href: "https://www.fbr.gov.pk/", label: copy("fbrLaws") }] : []).map((link) => (
              <li key={link.href}>
                <a href={link.href} target="_blank" rel="noopener noreferrer" className="text-sm text-seal">
                  {link.label}
                </a>
              </li>
            ))}
            {(kind === "declined" ? [{ href: "https://iris.fbr.gov.pk/", label: copy("iris") }] : []).map((link) => (
              <li key={link.href}>
                <a href={link.href} target="_blank" rel="noopener noreferrer" className="text-sm text-seal">
                  {link.label}
                </a>
              </li>
            ))}
            {official.map((link) => (
              <li key={link.url}>
                <a href={safeHref(link.url) ?? undefined} target="_blank" rel="noopener noreferrer" className="text-sm text-seal">
                  {link.label}
                  <span className="text-muted"> · {link.authority}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="border-t border-rule px-4 py-3 text-sm text-muted">
        {kind === "evidence" ? (
          <details>
            <summary className="cursor-pointer font-medium">{copy("refusalSearched")}</summary>
            {query ? <p className="mt-2 bg-elevated px-2 py-2 text-ink" dir="ltr">{query}</p> : null}
            <p className="mt-2">{retrieved == null ? copy("stepNone") : `${retrieved} · ${copy("stepRetrieved")}`}</p>
          </details>
        ) : (
          <p>
            {kind === "scope"
              ? copy("refusalNotSearchedScope")
              : kind === "declined"
                ? copy("refusalNotSearchedDeclined")
                : copy("refusalNotSearchedProvincial")}
          </p>
        )}
      </div>
    </div>
  )
}
