/** Filing details row + its edit popover, at the foot of both sidebars. */

import { useCallback, useId, useState } from "react"
import { FilingPopover } from "../features/onboarding/ProfilePanel"
import type { CopyKey } from "../i18n"
import type { ClientTaxYear, Profile } from "../lib/session"
import Icon from "./icons"
import { filingSummary } from "./nav"

type Copy = (key: CopyKey) => string

export default function FilingRow({
  profile,
  taxYear,
  taxYearSet,
  filingSaved,
  copy,
  onProfile,
  onTaxYear,
  onClearFiling,
}: {
  profile: Profile
  taxYear: ClientTaxYear
  taxYearSet: boolean
  filingSaved: boolean
  copy: Copy
  onProfile: (patch: Partial<Profile>) => void
  onTaxYear: (taxYear: ClientTaxYear) => void
  onClearFiling: () => void
}) {
  const popoverId = useId()
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  return (
    <div className={`filing${open ? " open" : ""}`}>
      {open ? (
        <FilingPopover
          id={popoverId}
          profile={profile}
          taxYear={taxYear}
          taxYearSet={taxYearSet}
          copy={copy}
          onChange={onProfile}
          onTaxYear={onTaxYear}
          onClear={onClearFiling}
          onClose={close}
        />
      ) : null}
      <button
        type="button"
        data-filing-row
        className="filing-row"
        title={copy("profileTitle")}
        aria-expanded={open}
        aria-controls={open ? popoverId : undefined}
        aria-haspopup="dialog"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="av">
          <Icon name="user" size="sm" />
        </span>
        <span className="lbl fr-t">
          <b>{copy("profileTitle")}</b>
          <small data-filing-summary>{filingSummary(profile, taxYear, taxYearSet, filingSaved, copy)}</small>
        </span>
        <Icon name="chev" size="sm" className="lbl updown" />
      </button>
    </div>
  )
}
