/** Reference strings, links and citation markers for answer sources (SPEC §9). */

import type { Source } from "../../../api/chat"
import { safeHref } from "../../../lib/safeUrl"

/** Short document names used on cards and in the panel ("ITO 2001 · s.149"). Unknown titles show in full. */
const SHORT_DOC: Record<string, string> = {
  "Income Tax Ordinance, 2001": "ITO 2001",
  "Income Tax Rules, 2002": "ITR 2002",
  "Sales Tax Act, 1990": "STA 1990",
  "Federal Excise Act, 2005": "FEA 2005",
  "Customs Act, 1969": "CA 1969",
}

export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => (key in values ? String(values[key]) : match))
}

export function docShort(source: Source): string {
  return SHORT_DOC[source.title] ?? source.title
}

/** "s.149" for numbered sections, otherwise the section as given, otherwise the document. */
export function sectionRef(source: Source): string {
  if (source.library === "web") return siteOf(source)
  if (!source.section) return docShort(source)
  return /^\d/.test(source.section) ? `s.${source.section}` : source.section
}

export function fullRef(source: Source): string {
  if (source.library === "web") return siteOf(source)
  return source.section ? `${docShort(source)} · ${sectionRef(source)}` : docShort(source)
}

/** "Income Tax Ordinance, 2001, s.149, p.212 (TY2026)" */
export function copyReference(source: Source, taxYear: string | null): string {
  if (source.library === "web") {
    return [source.title, safeHref(source.url) ?? siteOf(source)].filter(Boolean).join(", ")
  }
  const parts = [source.title]
  if (source.section) parts.push(sectionRef(source))
  if (source.page != null) parts.push(`p.${source.page}`)
  return `${parts.join(", ")}${taxYear ? ` (${/^TY/.test(taxYear) ? taxYear : `TY${taxYear}`})` : ""}`
}

export function siteOf(source: Source): string {
  if (source.site) return source.site
  try {
    return new URL(source.url).hostname.replace(/^www\./, "")
  } catch {
    return source.title
  }
}

/** The PDF link for a library source, opened at its page. */
export function pdfHref(source: Source): string | null {
  const base = safeHref(source.url) ?? safeHref(source.mirror_url)
  if (!base) return null
  return source.page != null ? `${base.split("#")[0]}#page=${source.page}` : base
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return ""
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Karachi",
  }).format(date)
}

/** Library sources first (they carry the [n] numbers), then web. */
export function citable(sources: Source[]): Source[] {
  return sources.filter((source) => Boolean(source.section || source.url || source.snippet))
}

/**
 * Turns "[n]" markers that point at a real source into markdown links "#cite-n".
 * Markers with no matching source stay as plain text; nothing is invented (SPEC §9).
 */
export function linkCitations(markdown: string, count: number): string {
  return markdown.replace(/\[(\d{1,2})\](?![(:[])/g, (match, digits: string) => {
    const n = Number(digits)
    return n >= 1 && n <= count ? `[${n}](#cite-${n})` : match
  })
}

/** Distinct, valid marker numbers in the answer, in order of first use. */
export function citedNumbers(markdown: string, count: number): number[] {
  const seen: number[] = []
  for (const match of markdown.matchAll(/\[(\d{1,2})\](?![(:[])/g)) {
    const n = Number(match[1])
    if (n >= 1 && n <= count && !seen.includes(n)) seen.push(n)
  }
  return seen
}
