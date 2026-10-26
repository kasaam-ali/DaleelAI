/** Writes a rupee amount, and adds a lakh or crore hint from 1 lakh up. */

const CRORE = 10_000_000
const LAKH = 100_000
const MONEY = /(Rs\.?|PKR)\s*(\d[\d,]*\d|\d+)(\s*\([^)]*\))?/gi

function words(amount: number): string | null {
  const abs = Math.abs(amount)
  if (abs >= CRORE) return `${trim(abs / CRORE)} crore`
  if (abs >= LAKH) return `${trim(abs / LAKH)} lakh`
  return null
}

function trim(value: number): string {
  return String(Math.round(value * 100) / 100)
}

/** "Rs 1,800,000 (18 lakh)". Amounts under 1 lakh stay as rupees only. */
export function formatPkr(amount: number): string {
  const grouped = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(amount)
  const hint = words(amount)
  return hint ? `Rs ${grouped} (${hint})` : `Rs ${grouped}`
}

/** Append a lakh or crore hint to rupee amounts already written in the text. */
export function annotatePkr(text: string): string {
  return text.replace(MONEY, (full, label: string, raw: string, existing: string | undefined) => {
    if (existing) return full
    const amount = Number(raw.replace(/,/g, ""))
    if (!Number.isFinite(amount)) return full
    const hint = words(amount)
    return hint ? `${label} ${raw} (${hint})` : full
  })
}
