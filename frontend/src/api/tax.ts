import { API_URL } from "./client"

export type TaxYear = "TY2026" | "TY2027"

export type BreakdownLine = {
  label: string
  base: number
  rate: number | null
  tax: number
  source: { law: string; ref: string }
}

export type Calculation = {
  tax_year: TaxYear
  inputs: Record<string, string | number>
  total_tax: number
  effective_rate: number
  breakdown: BreakdownLine[]
  notes: string[]
  rules_version: string
  compared_to: { tax_year: string; total_tax: number; difference: number } | null
  monthly_tax?: number
  net_annual?: number
  net_monthly?: number
}

export type FilerComparison = {
  tax_year: TaxYear
  rows: {
    type: string
    amount: number
    filer_tax: number
    late_filer_tax: number | null
    non_filer_tax: number
    difference: number
    source: { law: string; ref: string }
  }[]
  filer_total: number
  non_filer_total: number
  savings: number
  notes: string[]
  rules_version: string
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  })
  const data = (await response.json()) as { error?: { message?: string } }
  if (!response.ok) {
    throw new Error(data.error?.message || "The tax service could not calculate that.")
  }
  return data as T
}

export function calculateSalary(body: {
  tax_year: TaxYear
  annual_income?: number
  monthly_income?: number
}): Promise<Calculation> {
  return postJson("/api/v1/calculator/salary", body)
}

export function calculateFreelancer(body: {
  tax_year: TaxYear
  annual_receipts: number
  regime: "pseb_export" | "export_services" | "local_services"
  filer_status: "filer" | "non_filer"
}): Promise<Calculation> {
  return postJson("/api/v1/calculator/freelancer", body)
}

export function calculateProperty(body: {
  tax_year: TaxYear
  side: "purchase" | "sale"
  value: number
  filer_status: "filer" | "late_filer" | "non_filer"
}): Promise<Calculation> {
  return postJson("/api/v1/calculator/property", body)
}

export function compareFiler(body: {
  tax_year: TaxYear
  transactions: { type: string; amount: number; engine_cc?: number }[]
}): Promise<FilerComparison> {
  return postJson("/api/v1/compare/filer", body)
}
