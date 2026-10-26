/** The law date comes from the catalog: newest active FBR act, never SECP. */

import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { t } from "../i18n"
import { fbrLawDate, formatLawDate, lawDateLabel, parseCsv } from "./lawDate"

const catalog = readFileSync(join(__dirname, "..", "..", "..", "backend", "pipeline", "catalog.csv"), "utf8")
const HEAD = "doc_id,work_id,title,doc_type,domain,authority,language,amended_upto,tax_years,status,superseded_by,source_url,local_file,sha256,notes"

describe("FBR law date", () => {
  it("reads 30 Jun 2026 (Finance Act 2026) from the real catalog, in EN and Roman Urdu", () => {
    const value = fbrLawDate(catalog)
    expect(value).toEqual({ date: "2026-06-30", financeAct: "Finance Act 2026" })
    expect(lawDateLabel(t("en", "trust3Title"), value)).toBe("FBR laws updated to 30 Jun 2026 (Finance Act 2026)")
    expect(lawDateLabel(t("roman_urdu", "trust3Title"), value)).toBe("FBR qawaneen 30 Jun 2026 tak updated (Finance Act 2026)")
    expect(__FBR_LAW_DATE__).toEqual(value)
  })

  it("ignores SECP, expired rows, and non-act rows like newer SROs or circulars", () => {
    const csv = [
      HEAD,
      'companies_act,companies_act,"Companies Act, 2017",act,corporate,SECP,en,2030-01-01,,active,,,,,',
      'old,old,"Old Act",act,income_tax,FBR,en,2029-06-30,,expired,,,,,',
      'sro,sro,"SRO 1, with comma",sro,sales_tax,FBR,en,2028-01-01,,active,,,,,',
      'ito,ito,"Income Tax Ordinance, 2001",act,income_tax,FBR,en,2027-06-30,,active,,,,,',
      'fa,fa,"Finance Act, 2027",finance_act,general,FBR,en,2027-06-29,,active,,,,,',
    ].join("\n")
    expect(fbrLawDate(csv)).toEqual({ date: "2027-06-30", financeAct: "Finance Act 2027" })
    expect(parseCsv(csv)[2].title).toBe("SRO 1, with comma")
  })

  it("drops the Finance Act part when there is none, and fails loudly without any act", () => {
    expect(lawDateLabel("FBR laws updated to {date} ({act})", { date: "2026-02-20", financeAct: null })).toBe("FBR laws updated to 20 Feb 2026")
    expect(formatLawDate("2026-12-01")).toBe("1 Dec 2026")
    expect(() => fbrLawDate(HEAD + "\n")).toThrow()
  })
})
