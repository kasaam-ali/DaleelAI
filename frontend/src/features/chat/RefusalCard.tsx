/** A limit of the library, not a failed request. */

import type { CSSProperties } from "react"
import type { ActionLink } from "../../api/chat"
import type { CopyKey } from "../../i18n"
import { safeHref } from "../../lib/safeUrl"
import Icon, { type IconName } from "../../shell/icons"
import type { RefusalKind } from "./refusal"

type Copy = (key: CopyKey) => string

/** Accent per kind (SPEC §5.2A item 9): evidence violet, scope link blue, declined red, provincial amber. */
const ACCENT: Record<RefusalKind, { k: string; soft: string; icon: IconName }> = {
  evidence: { k: "var(--refusal)", soft: "var(--refusal-soft)", icon: "compass" },
  scope: { k: "var(--link)", soft: "color-mix(in srgb, var(--link) 12%, var(--field))", icon: "map" },
  declined: { k: "var(--error)", soft: "var(--error-soft)", icon: "ban" },
  provincial: { k: "var(--warn)", soft: "var(--warn-soft)", icon: "map" },
}

const TITLE: Record<RefusalKind, CopyKey> = {
  evidence: "refusalEvidenceTitle",
  scope: "refusalScopeTitle",
  declined: "refusalDeclinedTitle",
  provincial: "refusalProvincialTitle",
}

/** The prompt-injection refusal (EN or Roman Urdu) is not an evasion refusal. */
const INJECTION = /reveal a hidden prompt|chhupa hua prompt/i

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

const OFFICIAL: Record<RefusalKind, CopyKey> = {
  evidence: "refusalOfficial",
  scope: "refusalOfficial",
  declined: "refusalDeclinedOfficial",
  provincial: "refusalProvincialOfficial",
}

const NOT_SEARCHED: Record<Exclude<RefusalKind, "evidence">, CopyKey> = {
  scope: "refusalNotSearchedScope",
  declined: "refusalNotSearchedDeclined",
  provincial: "refusalNotSearchedProvincial",
}

type LinkRow = { href: string; title: string; detail: string; external: boolean }

export default function RefusalCard({
  kind,
  reason,
  authority,
  query,
  retrieved,
  rerankTop = null,
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
  rerankTop?: number | null
  suggestions: string[]
  links: ActionLink[]
  copy: Copy
  onAsk: (question: string) => void
}) {
  const chips = suggestions.length > 0 ? suggestions : FALLBACK[kind].map((key) => copy(key))
  const injection = kind === "declined" && INJECTION.test(reason)
  const title =
    kind === "provincial" && authority
      ? `${copy("handledBy")} ${authority}`
      : copy(injection ? "refusalInjectionTitle" : TITLE[kind])
  const helpline: LinkRow = { href: "tel:051111772772", title: copy("helpline"), detail: copy("helplineHours"), external: false }
  const fixed: LinkRow[] =
    kind === "evidence"
      ? [helpline, { href: "https://www.fbr.gov.pk/", title: copy("fbrLaws"), detail: copy("fbrLawsDetail"), external: true }]
      : kind === "declined"
        ? [{ href: "https://iris.fbr.gov.pk/", title: copy("iris"), detail: copy("irisDetail"), external: true }, { ...helpline, detail: copy("helplineDetail") }]
        : []
  const official: LinkRow[] = [
    ...fixed,
    ...links.flatMap((link) => {
      const href = safeHref(link.url)
      return href ? [{ href, title: link.label, detail: link.authority, external: true }] : []
    }),
  ]
  const accent = ACCENT[kind]
  const style = { "--k": accent.k, "--k-soft": accent.soft } as CSSProperties
  const tryBlock = (
    <div className="rsec">
      <h4>{copy(TRY[kind])}</h4>
      <div className="rchips">
        {chips.map((question) => (
          <button key={question} type="button" onClick={() => onAsk(question)}>
            <Icon name="arrow" size="sm" />
            {question}
          </button>
        ))}
      </div>
    </div>
  )
  const linkBlock =
    official.length > 0 ? (
      <div className="rsec">
        <h4>{copy(OFFICIAL[kind])}</h4>
        <div className="rlinks">
          {official.map((link) => (
            <a
              key={link.href + link.title}
              className="rlink"
              href={link.href}
              {...(link.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
            >
              <Icon name="globe" size="sm" />
              <span>
                <b>{link.title}</b>
                <small>{link.detail}</small>
              </span>
              <Icon name="chev" size="sm" />
            </a>
          ))}
        </div>
      </div>
    ) : null
  return (
    <div data-motion-slot="refusal-card" data-kind={kind} className="card rcard" style={style}>
      <div className="rhead">
        <span className="ri">
          <Icon name={accent.icon} />
        </span>
        <div>
          <span className="kind">{copy(LABEL[kind])}</span>
          <h3>{title}</h3>
          <p>{reason}</p>
        </div>
      </div>
      {kind === "provincial" ? (
        <>
          {linkBlock}
          {tryBlock}
        </>
      ) : (
        <>
          {tryBlock}
          {linkBlock}
        </>
      )}
      <div className="rsec">
        {kind === "evidence" ? (
          <details className="searched" open>
            <summary>
              <Icon name="search" size="sm" />
              {copy("refusalSearched")}
              <Icon name="chev" size="sm" className="chev" />
            </summary>
            {query ? (
              <span className="sq" dir="ltr">
                <Icon name="search" size="sm" />
                {query}
              </span>
            ) : null}
            <p className="scount">{copy("refusalTraceNote")}</p>
            <div className="miss">
              <b>{copy("refusalRowRetrieved")}</b>
              <span>{retrieved == null ? copy("stepNone") : String(retrieved)}</span>
              <i aria-hidden="true">
                <em style={{ width: retrieved ? "100%" : "0%" }} />
              </i>
            </div>
            <div className="miss">
              <b>{copy("refusalRowRerank")}</b>
              <span>{rerankTop == null ? copy("stepNone") : rerankTop.toFixed(2)}</span>
              <i aria-hidden="true">
                <em style={{ width: `${Math.round(Math.max(0, Math.min(1, rerankTop ?? 0)) * 100)}%` }} />
              </i>
            </div>
            <div className="miss">
              <b>{copy("refusalRowVerified")}</b>
              <span>0 · {copy("refusalNoAnswer")}</span>
              <i aria-hidden="true">
                <em style={{ width: "0%" }} />
              </i>
            </div>
          </details>
        ) : (
          <p className="notsearched">
            <Icon name="info" size="sm" />
            {copy(NOT_SEARCHED[kind])}
          </p>
        )}
      </div>
    </div>
  )
}
