/** Filing details step at the top of Home (SPEC §5.1): empty, partial (n of 4) and the saved summary. */

import type { CSSProperties } from "react"
import type { CopyKey } from "../../i18n"
import { filingCount, filingReady, type ClientTaxYear, type Profile, type Province, type TaxpayerType } from "../../lib/session"
import { FILERS, PROVINCES, TAXPAYERS, TAX_YEARS, labelFor } from "./filing"
import Icon from "../../shell/icons"

type Copy = (key: CopyKey) => string

function Segments<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: { value: T; label: string }[]
  value: T | null
  onChange: (value: T) => void
}) {
  return (
    <div className="sg" role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={option.value === value}
          className={option.value === value ? "on" : ""}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

function Select({
  id,
  value,
  placeholder,
  options,
  onChange,
}: {
  id: string
  value: string
  placeholder: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}) {
  return (
    <div className="sel">
      <select id={id} value={value} className={value ? "" : "empty"} onChange={(event) => onChange(event.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <Icon name="chev" size="sm" className="chev" />
    </div>
  )
}

export default function FilingStep({
  profile,
  taxYear,
  taxYearSet,
  saved,
  copy,
  onChange,
  onTaxYear,
  onSave,
  onEdit,
  inSheet = false,
}: {
  profile: Profile
  taxYear: ClientTaxYear
  taxYearSet: boolean
  saved: boolean
  copy: Copy
  onChange: (patch: Partial<Profile>) => void
  onTaxYear: (taxYear: ClientTaxYear) => void
  onSave: () => void
  onEdit: () => void
  /** Rendered inside the phone filing sheet (SPEC §10.1): the sheet supplies the title. */
  inSheet?: boolean
}) {
  const sheet = inSheet ? " in-sheet" : ""
  const ready = filingReady(profile)
  const count = filingCount(profile, taxYearSet)

  if (saved && ready) {
    const pills: [string, string][] = [
      [copy("fsFiler"), labelFor(FILERS, profile.filer_status, copy)],
      [copy("fsTaxpayer"), labelFor(TAXPAYERS, profile.taxpayer_type, copy)],
      ...(profile.province ? ([[copy("fsProvince"), labelFor(PROVINCES, profile.province, copy)]] as [string, string][]) : []),
      [copy("taxYearLabel"), taxYear],
    ]
    return (
      <section className={`card fstep fsaved${sheet}`} data-reveal style={{ "--i": 0 } as CSSProperties} aria-label={copy("fsSaved")} data-state="saved">
        <span className="okdot">
          <Icon name="check" size="sm" />
        </span>
        <b>{copy("fsSaved")}</b>
        <div className="pills">
          {pills.map(([label, value]) => (
            <span key={label} className="pill">
              <span>{label}</span>
              {value}
            </span>
          ))}
        </div>
        <span className="note">{copy("fsSentNote")}</span>
        <button type="button" className="btn ghost" onClick={onEdit}>
          {copy("fsEdit")}
        </button>
      </section>
    )
  }

  const progress = copy("fsOf").replace("{n}", String(count))
  return (
    <section className={`card fstep${sheet}`} data-reveal style={{ "--i": 0 } as CSSProperties} aria-labelledby="fs-title" data-state={count > 0 ? "partial" : "empty"}>
      <div className="fs-head">
        <span className="fs-ic">
          <Icon name="user" size="sm" />
        </span>
        <span className="fs-t">
          <b id="fs-title">{copy("fsTitle")}</b>
          <small>{copy("fsSub")}</small>
        </span>
        <span className="fs-sp" />
        <span className="prog" aria-label={progress}>
          {[0, 1, 2, 3].map((index) => (
            <i key={index} className={index < count ? "on" : ""} />
          ))}
          <span aria-hidden="true">{progress}</span>
        </span>
        <button
          type="button"
          className="btn"
          aria-disabled={!ready}
          onClick={() => {
            if (ready) onSave()
          }}
        >
          <Icon name="check" size="sm" />
          {copy("fsSave")}
        </button>
      </div>
      <div className="fs-grid">
        <div className="fld">
          <span className="lab">{copy("fsFiler")}</span>
          <Segments
            label={copy("fsFiler")}
            value={profile.filer_status}
            options={FILERS.map((item) => ({ value: item.value, label: copy(item.label) }))}
            onChange={(value) => onChange({ filer_status: value })}
          />
        </div>
        <div className="fld">
          <label htmlFor="fs-taxpayer">{copy("fsTaxpayer")}</label>
          <Select
            id="fs-taxpayer"
            value={profile.taxpayer_type ?? ""}
            placeholder={copy("fsChoose")}
            options={TAXPAYERS.map((item) => ({ value: item.value, label: copy(item.label) }))}
            onChange={(value) => onChange({ taxpayer_type: (value || null) as TaxpayerType | null })}
          />
        </div>
        <div className="fld">
          <label htmlFor="fs-province">
            {copy("fsProvince")} <em>· {copy("fsOptional")}</em>
          </label>
          <Select
            id="fs-province"
            value={profile.province ?? ""}
            placeholder={copy("fsChoose")}
            options={PROVINCES.map((item) => ({ value: item.value, label: copy(item.label) }))}
            onChange={(value) => onChange({ province: (value || null) as Province | null })}
          />
        </div>
        <div className="fld">
          <span className="lab">{copy("taxYearLabel")}</span>
          <Segments
            label={copy("taxYearLabel")}
            value={taxYearSet ? taxYear : null}
            options={TAX_YEARS.map((year) => ({ value: year, label: year }))}
            onChange={onTaxYear}
          />
        </div>
      </div>
    </section>
  )
}
