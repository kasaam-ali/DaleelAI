/** Optional questions: taxpayer type, filer status, and province. */

import { useEffect, useRef } from "react"
import type { CopyKey } from "../../i18n"
import type { ClientTaxYear, FilerStatus, Profile, Province, TaxpayerType } from "../../lib/session"
import { FILERS, PROVINCES, TAXPAYERS, TAX_YEARS } from "../home/filing"
import Icon from "../../shell/icons"
import { useModal } from "../../shell/useModal"

type Copy = (key: CopyKey) => string

const PANEL_TAXPAYERS: { value: TaxpayerType; label: CopyKey }[] = [
  { value: "salaried", label: "salaried" },
  { value: "freelancer", label: "freelancer" },
  { value: "business", label: "business" },
  { value: "company", label: "company" },
]

const PANEL_FILERS: { value: FilerStatus; label: CopyKey }[] = [
  { value: "filer", label: "filer" },
  { value: "non_filer", label: "nonFiler" },
  { value: "unknown", label: "notSure" },
]

const PANEL_PROVINCES: { value: Province; label: CopyKey }[] = [
  { value: "punjab", label: "punjab" },
  { value: "sindh", label: "sindh" },
  { value: "kpk", label: "kpk" },
  { value: "balochistan", label: "balochistan" },
  { value: "islamabad", label: "islamabad" },
  { value: "gb", label: "gb" },
  { value: "ajk", label: "ajk" },
]

export default function ProfilePanel({
  profile,
  copy,
  onChange,
  compact = false,
  idPrefix = "",
}: {
  profile: Profile
  copy: Copy
  onChange: (patch: Partial<Profile>) => void
  compact?: boolean
  idPrefix?: string
}) {
  return (
    <section className={compact ? "mt-2" : "mt-8"} aria-labelledby={compact ? undefined : "filing-details"}>
      {compact ? null : (
        <>
          <h2 id="filing-details" className="text-base font-medium">
            {copy("profileTitle")}
          </h2>
          <p className="mt-1 max-w-[68ch] text-sm text-muted">{copy("profileHelp")}</p>
        </>
      )}
      <div className={compact ? "grid gap-3" : "mt-4 grid gap-4 sm:grid-cols-3"}>
        <Field
          id={`${idPrefix}taxpayer-type`}
          label={copy("taxpayerType")}
          value={profile.taxpayer_type ?? ""}
          choose={copy("choose")}
          options={PANEL_TAXPAYERS.map((item) => ({ value: item.value, label: copy(item.label) }))}
          onChange={(value) => onChange({ taxpayer_type: (value || null) as TaxpayerType | null })}
        />
        <Field
          id={`${idPrefix}filer-status`}
          label={copy("filerStatus")}
          value={profile.filer_status ?? ""}
          choose={copy("choose")}
          options={PANEL_FILERS.map((item) => ({ value: item.value, label: copy(item.label) }))}
          onChange={(value) => onChange({ filer_status: (value || null) as FilerStatus | null })}
        />
        <Field
          id={`${idPrefix}province`}
          label={copy("province")}
          value={profile.province ?? ""}
          choose={copy("choose")}
          options={PANEL_PROVINCES.map((item) => ({ value: item.value, label: copy(item.label) }))}
          onChange={(value) => onChange({ province: (value || null) as Province | null })}
        />
      </div>
    </section>
  )
}

function Field({
  id,
  label,
  value,
  choose,
  options,
  onChange,
}: {
  id: string
  label: string
  value: string
  choose: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-11 w-full border border-rule bg-field px-3 text-base text-ink"
      >
        <option value="">{choose}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

/** Sidebar filing popover (shared.js `filing-pop`): the same four fields as the Home step, plus Clear. Replaces the inline panel. */
export function FilingPopover({
  id,
  profile,
  taxYear,
  taxYearSet,
  copy,
  onChange,
  onTaxYear,
  onClear,
  onClose,
}: {
  id: string
  profile: Profile
  taxYear: ClientTaxYear
  taxYearSet: boolean
  copy: Copy
  onChange: (patch: Partial<Profile>) => void
  onTaxYear: (taxYear: ClientTaxYear) => void
  onClear: () => void
  onClose: () => void
}) {
  const rootRef = useRef<HTMLDivElement>(null)

  useModal(true, rootRef, onClose)

  useEffect(() => {
    function onPointer(event: MouseEvent) {
      if (rootRef.current?.contains(event.target as Node)) return
      onClose()
    }
    document.addEventListener("mousedown", onPointer)
    return () => document.removeEventListener("mousedown", onPointer)
  }, [onClose])

  const rows: { id: string; label: string; value: string; options: { value: string; label: string }[]; set: (value: string) => void }[] = [
    {
      id: "taxpayer",
      label: copy("fsTaxpayer"),
      value: profile.taxpayer_type ?? "",
      options: TAXPAYERS.map((item) => ({ value: item.value, label: copy(item.label) })),
      set: (value) => onChange({ taxpayer_type: (value || null) as TaxpayerType | null }),
    },
    {
      id: "filer",
      label: copy("fsFiler"),
      value: profile.filer_status ?? "",
      options: FILERS.map((item) => ({ value: item.value, label: copy(item.label) })),
      set: (value) => onChange({ filer_status: (value || null) as FilerStatus | null }),
    },
    {
      id: "province",
      label: copy("fsProvince"),
      value: profile.province ?? "",
      options: PROVINCES.map((item) => ({ value: item.value, label: copy(item.label) })),
      set: (value) => onChange({ province: (value || null) as Province | null }),
    },
    {
      id: "year",
      label: copy("taxYearLabel"),
      value: taxYearSet ? taxYear : "",
      options: TAX_YEARS.map((year) => ({ value: year, label: year })),
      set: (value) => {
        if (value === "TY2026" || value === "TY2027") onTaxYear(value)
      },
    },
  ]

  return (
    <div ref={rootRef} id={id} role="dialog" aria-label={copy("profileTitle")} className="filing-pop">
      <p className="fp-h">{copy("profileTitle")}</p>
      <p className="filing-note">{copy("filingNote")}</p>
      {rows.map((row) => (
        <label key={row.id} className="fp-row" htmlFor={`fp-${row.id}`}>
          <span>{row.label}</span>
          <span className="fp-sel">
            <select id={`fp-${row.id}`} value={row.value} onChange={(event) => row.set(event.target.value)}>
              <option value="">{copy("fsChoose")}</option>
              {row.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <Icon name="chev" size="sm" className="rotate-90" />
          </span>
        </label>
      ))}
      <button type="button" className="fp-clear" onClick={onClear}>
        {copy("filingClear")}
      </button>
    </div>
  )
}
