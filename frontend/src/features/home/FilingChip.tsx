/** Phone filing details chip at the top of Home (SPEC §10.1, h01–h03); opens the filing sheet. */

import type { CopyKey } from "../../i18n"
import { filingCount, filingReady, type ClientTaxYear, type Profile } from "../../lib/session"
import Icon from "../../shell/icons"
import { filingSummary } from "../../shell/nav"

type Copy = (key: CopyKey) => string

export default function FilingChip({
  profile,
  taxYear,
  taxYearSet,
  saved,
  copy,
  onOpen,
}: {
  profile: Profile
  taxYear: ClientTaxYear
  taxYearSet: boolean
  saved: boolean
  copy: Copy
  onOpen: () => void
}) {
  const ok = saved && filingReady(profile)
  const count = filingCount(profile, taxYearSet)
  return (
    <button type="button" data-filing-chip className={`fchip${ok ? " ok" : ""}`} aria-haspopup="dialog" onClick={onOpen}>
      <span className="fc-ic">
        <Icon name={ok ? "check" : "user"} size="sm" />
      </span>
      <span className="fc-t">
        <b>{copy("profileTitle")}</b>
        <small>{filingSummary(profile, taxYear, taxYearSet, saved, copy)}</small>
      </span>
      {ok ? null : (
        <span className="fc-dots" aria-hidden="true">
          {[0, 1, 2, 3].map((index) => (
            <i key={index} className={index < count ? "on" : ""} />
          ))}
        </span>
      )}
      <Icon name="chev" size="sm" className="fc-chev" />
    </button>
  )
}
