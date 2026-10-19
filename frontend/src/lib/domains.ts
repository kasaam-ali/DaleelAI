import type { CopyKey } from "../i18n"

const KEYS: Record<string, CopyKey> = {
  income_tax: "domainIncome",
  sales_tax: "domainSales",
  customs: "domainCustoms",
  corporate_secp: "domainCorporate",
  audit_notice: "domainAudit",
  property: "domainProperty",
}

export function domainLabel(copy: (key: CopyKey) => string, value: string): string {
  const key = KEYS[value]
  return key ? copy(key) : value
}
