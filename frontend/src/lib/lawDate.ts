/** The "FBR laws updated to" date, read from backend/pipeline/catalog.csv at build time (vite.config.ts). */

export type LawDate = { date: string; financeAct: string | null }

/** Minimal CSV parser: quoted fields, doubled quotes, commas inside quotes. */
export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = []
  let row: string[] = []
  let field = ""
  let quoted = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"'
        i++
      } else if (ch === '"') quoted = false
      else field += ch
    } else if (ch === '"') quoted = true
    else if (ch === ",") {
      row.push(field)
      field = ""
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++
      row.push(field)
      field = ""
      if (row.some((cell) => cell !== "")) rows.push(row)
      row = []
    } else field += ch
  }
  if (field !== "" || row.length) {
    row.push(field)
    rows.push(row)
  }
  const [head, ...body] = rows
  return body.map((cells) => Object.fromEntries(head.map((key, index) => [key, cells[index] ?? ""])))
}

const ISO = /^\d{4}-\d{2}-\d{2}$/

/**
 * Latest `amended_upto` among active FBR statutes (doc_type "act"), plus the newest active FBR Finance Act.
 * SECP rows never count: the Companies Act in the library is the 18.08.2022 version.
 */
export function fbrLawDate(csv: string): LawDate {
  const rows = parseCsv(csv).filter((row) => row.status === "active" && row.authority === "FBR")
  const acts = rows.filter((row) => row.doc_type === "act" && ISO.test(row.amended_upto)).map((row) => row.amended_upto)
  if (acts.length === 0) throw new Error("catalog.csv has no active FBR act with an amended_upto date")
  const date = acts.sort().at(-1)!
  const finance = rows
    .filter((row) => row.doc_type === "finance_act" && ISO.test(row.amended_upto) && row.amended_upto <= date)
    .sort((a, b) => a.amended_upto.localeCompare(b.amended_upto))
    .at(-1)
  const year = finance?.title.match(/Finance Act,?\s*(\d{4})/)?.[1]
  return { date, financeAct: year ? `Finance Act ${year}` : null }
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

/** 2026-06-30 → "30 Jun 2026". */
export function formatLawDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number)
  return `${day} ${MONTHS[month - 1]} ${year}`
}

/** Fills the EN or Roman Urdu template: {date} and {act} (the act part is dropped when unknown). */
export function lawDateLabel(template: string, value: LawDate): string {
  const withAct = value.financeAct ? template.replace("{act}", value.financeAct) : template.replace(/\s*\(\{act\}\)/, "")
  return withAct.replace("{date}", formatLawDate(value.date))
}
