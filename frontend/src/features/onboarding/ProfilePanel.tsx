/** Optional questions: taxpayer type, filer status, and province. */

import type { CopyKey } from "../../i18n"
import type { FilerStatus, Profile, Province, TaxpayerType } from "../../lib/session"

type Copy = (key: CopyKey) => string

const TAXPAYERS: { value: TaxpayerType; label: CopyKey }[] = [
  { value: "salaried", label: "salaried" },
  { value: "freelancer", label: "freelancer" },
  { value: "business", label: "business" },
  { value: "company", label: "company" },
]

const FILERS: { value: FilerStatus; label: CopyKey }[] = [
  { value: "filer", label: "filer" },
  { value: "non_filer", label: "nonFiler" },
  { value: "unknown", label: "notSure" },
]

const PROVINCES: { value: Province; label: CopyKey }[] = [
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
          options={TAXPAYERS.map((item) => ({ value: item.value, label: copy(item.label) }))}
          onChange={(value) => onChange({ taxpayer_type: (value || null) as TaxpayerType | null })}
        />
        <Field
          id={`${idPrefix}filer-status`}
          label={copy("filerStatus")}
          value={profile.filer_status ?? ""}
          choose={copy("choose")}
          options={FILERS.map((item) => ({ value: item.value, label: copy(item.label) }))}
          onChange={(value) => onChange({ filer_status: (value || null) as FilerStatus | null })}
        />
        <Field
          id={`${idPrefix}province`}
          label={copy("province")}
          value={profile.province ?? ""}
          choose={copy("choose")}
          options={PROVINCES.map((item) => ({ value: item.value, label: copy(item.label) }))}
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
