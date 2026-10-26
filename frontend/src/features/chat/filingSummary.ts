/** One-line filing context ("Freelancer · Filer · Punjab · TY2026") for New chat and the answer header. */

import type { CopyKey } from "../../i18n"
import type { ClientTaxYear, FilerStatus, Profile, Province, TaxpayerType } from "../../lib/session"

type Copy = (key: CopyKey) => string

const TAXPAYER: Record<TaxpayerType, CopyKey> = {
  salaried: "salaried",
  freelancer: "freelancer",
  business: "business",
  company: "company",
}

const FILER: Record<FilerStatus, CopyKey> = {
  filer: "filer",
  non_filer: "nonFiler",
  unknown: "notSure",
}

const PROVINCE: Record<Province, CopyKey> = {
  punjab: "punjab",
  sindh: "sindh",
  kpk: "kpk",
  balochistan: "balochistan",
  islamabad: "islamabad",
  gb: "gb",
  ajk: "ajk",
}

export function filingSummary(profile: Profile, taxYear: ClientTaxYear, copy: Copy) {
  const parts = [
    profile.taxpayer_type ? copy(TAXPAYER[profile.taxpayer_type]) : null,
    profile.filer_status ? copy(FILER[profile.filer_status]) : null,
    profile.province ? copy(PROVINCE[profile.province]) : null,
    taxYear,
  ].filter((part): part is string => Boolean(part))
  return parts.join(" · ")
}
