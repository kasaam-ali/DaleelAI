import { useState, type FormEvent } from "react"
import { compareFiler, type FilerComparison, type TaxYear } from "../../api/tax"
import type { CopyKey } from "../../i18n"
import { formatPkr } from "../../lib/money"
import { CompareBars } from "../tax/CompareBars"

type Copy = (key: CopyKey) => string

const TYPES = [
  "property_purchase",
  "property_sale",
  "vehicle_registration",
  "vehicle_token",
  "dividend",
  "profit_on_debt",
] as const

const inputClass = "mt-1 min-h-11 w-full border border-rule bg-field px-3 text-base text-ink"

export default function FilerPage({
  copy,
  onOpenChecklist,
}: {
  copy: Copy
  onOpenChecklist?: (templateId: string) => void
}) {
  const [taxYear, setTaxYear] = useState<TaxYear>("TY2027")
  const [type, setType] = useState<(typeof TYPES)[number]>("property_purchase")
  const [amount, setAmount] = useState("10000000")
  const [engineCc, setEngineCc] = useState("1300")
  const [result, setResult] = useState<FilerComparison | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const needsCc = type.startsWith("vehicle")

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const value = Number(amount.replace(/,/g, ""))
    const cc = Number(engineCc)
    if (!Number.isInteger(value) || value < 0) {
      setError(copy("amountWhole"))
      return
    }
    if (needsCc && (!Number.isInteger(cc) || cc <= 0)) {
      setError(copy("ccWhole"))
      return
    }
    setBusy(true)
    setError(null)
    try {
      const next = await compareFiler({
        tax_year: taxYear,
        transactions: [
          needsCc ? { type, amount: value, engine_cc: cc } : { type, amount: value },
        ],
      })
      setResult(next)
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : copy("calcFailed"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="mt-8" aria-labelledby="filer-title">
      <h2 id="filer-title" className="text-base font-medium">
        {copy("filerTitle")}
      </h2>
      <p className="mt-1 max-w-[68ch] text-sm text-muted">{copy("filerHelp")}</p>
      <form onSubmit={(event) => void onSubmit(event)} className="mt-4 grid gap-4">
        <label className="text-sm">
          {copy("taxYear")}
          <select
            value={taxYear}
            onChange={(event) => setTaxYear(event.target.value as TaxYear)}
            className={inputClass}
          >
            <option value="TY2027">TY2027</option>
            <option value="TY2026">TY2026</option>
          </select>
        </label>
        <label className="text-sm">
          {copy("transactionType")}
          <select
            value={type}
            onChange={(event) => setType(event.target.value as (typeof TYPES)[number])}
            className={inputClass}
          >
            {TYPES.map((item) => (
              <option key={item} value={item}>
                {copy(item)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          {copy("amount")}
          <input
            inputMode="numeric"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            className={inputClass}
          />
        </label>
        {needsCc ? (
          <label className="text-sm">
            {copy("engineCc")}
            <input
              inputMode="numeric"
              value={engineCc}
              onChange={(event) => setEngineCc(event.target.value)}
              className={inputClass}
            />
          </label>
        ) : null}
        <button
          type="submit"
          disabled={busy}
          className="min-h-11 bg-seal px-4 text-sm font-medium text-seal-ink disabled:bg-rule disabled:text-muted"
        >
          {busy ? copy("calculating") : copy("compare")}
        </button>
      </form>
      {error ? (
        <p className="mt-4 text-sm text-low" role="alert">
          {error}
        </p>
      ) : null}
      {result ? (
        <div className="mt-6 border border-rule bg-field px-4 py-4">
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th className="py-2 font-medium">{copy("filer")}</th>
                <th className="py-2 font-medium">{copy("nonFiler")}</th>
                <th className="py-2 font-medium">{copy("lateFiler")}</th>
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row) => (
                <tr key={row.type}>
                  <td className="py-2">{formatPkr(row.filer_tax)}</td>
                  <td className="py-2">{formatPkr(row.non_filer_tax)}</td>
                  <td className="py-2">{row.late_filer_tax == null ? copy("notInYear") : formatPkr(row.late_filer_tax)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <CompareBars
            leftLabel={copy("filerBar")}
            left={result.filer_total}
            rightLabel={copy("nonFilerBar")}
            right={result.non_filer_total}
          />
          <p className="mt-3 text-sm">
            {copy("extraIfNotFiler")} {formatPkr(result.savings)}
          </p>
          {onOpenChecklist ? (
            <button
              type="button"
              onClick={() => onOpenChecklist("ntn_individual")}
              className="mt-3 min-h-11 border border-rule px-3 text-sm"
            >
              {copy("becomeFiler")}
            </button>
          ) : null}
          <p className="mt-1 text-sm text-muted">
            {copy("rulesVersion")} {result.rules_version}
          </p>
          {result.rows[0] ? (
            <p className="mt-2 max-w-[68ch] text-sm text-muted">{result.rows[0].source.ref}</p>
          ) : null}
          {result.notes.map((note) => (
            <p key={note} className="mt-2 max-w-[68ch] text-sm text-muted">
              {note}
            </p>
          ))}
        </div>
      ) : null}
    </section>
  )
}
