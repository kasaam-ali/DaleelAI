import { useState, type FormEvent } from "react"
import {
  calculateFreelancer,
  calculateProperty,
  calculateSalary,
  type Calculation,
  type TaxYear,
} from "../../api/tax"
import type { CopyKey } from "../../i18n"
import { formatPkr } from "../../lib/money"
import { chip, field, primary, secondary } from "../../ui/styles"
import { CompareBars } from "../tax/CompareBars"

type Copy = (key: CopyKey) => string
type Tool = "salary" | "freelancer" | "property"

const inputClass = field

export default function CalculatorPage({
  copy,
  onOpenChecklist,
}: {
  copy: Copy
  onOpenChecklist?: (templateId: string) => void
}) {
  const [tool, setTool] = useState<Tool>("salary")
  const [taxYear, setTaxYear] = useState<TaxYear>("TY2027")
  const [amount, setAmount] = useState("1200000")
  const [monthly, setMonthly] = useState(false)
  const [regime, setRegime] = useState<"pseb_export" | "export_services" | "local_services">("pseb_export")
  const [filerStatus, setFilerStatus] = useState<"filer" | "non_filer" | "late_filer">("filer")
  const [side, setSide] = useState<"purchase" | "sale">("purchase")
  const [result, setResult] = useState<Calculation | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const value = Number(amount.replace(/,/g, ""))
    if (!Number.isInteger(value) || value < 0) {
      setError(copy("amountWhole"))
      return
    }
    setBusy(true)
    setError(null)
    try {
      const next =
        tool === "salary"
          ? await calculateSalary(
              monthly
                ? { tax_year: taxYear, monthly_income: value }
                : { tax_year: taxYear, annual_income: value },
            )
          : tool === "freelancer"
            ? await calculateFreelancer({
                tax_year: taxYear,
                annual_receipts: value,
                regime,
                filer_status: filerStatus === "late_filer" ? "filer" : filerStatus,
              })
            : await calculateProperty({
                tax_year: taxYear,
                side,
                value,
                filer_status: filerStatus,
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
    <section aria-labelledby="calculator-title">
      <h2 id="calculator-title" className="font-statute text-3xl tracking-tight">
        {copy("calcTitle")}
      </h2>
      <p className="mt-2 max-w-[62ch] text-sm leading-6 text-muted">{copy("calcHelp")}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {(
          [
            ["salary", "calcSalary"],
            ["freelancer", "calcFreelancer"],
            ["property", "calcProperty"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            aria-pressed={tool === id}
            onClick={() => {
              setTool(id)
              setResult(null)
            }}
            className={chip(tool === id)}
          >
            {copy(label)}
          </button>
        ))}
      </div>
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
          {tool === "property" ? copy("propertyValue") : monthly ? copy("monthlyIncome") : copy("annualIncome")}
          <input
            inputMode="numeric"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            className={inputClass}
          />
        </label>
        {tool === "salary" ? (
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input type="checkbox" checked={monthly} onChange={(event) => setMonthly(event.target.checked)} />
            {copy("useMonthly")}
          </label>
        ) : null}
        {tool === "freelancer" ? (
          <label className="text-sm">
            {copy("regime")}
            <select
              value={regime}
              onChange={(event) => setRegime(event.target.value as typeof regime)}
              className={inputClass}
            >
              <option value="pseb_export">{copy("psebExport")}</option>
              <option value="export_services">{copy("exportServices")}</option>
              <option value="local_services">{copy("localServices")}</option>
            </select>
          </label>
        ) : null}
        {tool === "property" ? (
          <label className="text-sm">
            {copy("propertySide")}
            <select
              value={side}
              onChange={(event) => setSide(event.target.value as typeof side)}
              className={inputClass}
            >
              <option value="purchase">{copy("purchase")}</option>
              <option value="sale">{copy("sale")}</option>
            </select>
          </label>
        ) : null}
        {tool !== "salary" ? (
          <label className="text-sm">
            {copy("filerStatus")}
            <select
              value={filerStatus}
              onChange={(event) => setFilerStatus(event.target.value as typeof filerStatus)}
              className={inputClass}
            >
              <option value="filer">{copy("filer")}</option>
              <option value="non_filer">{copy("nonFiler")}</option>
              {tool === "property" ? <option value="late_filer">{copy("lateFiler")}</option> : null}
            </select>
          </label>
        ) : null}
        <button
          type="submit"
          disabled={busy}
          className={`${primary} w-full sm:w-auto`}
        >
          {busy ? copy("calculating") : copy("calculate")}
        </button>
      </form>
      {error ? (
        <p className="mt-4 text-sm text-low" role="alert">
          {error}
        </p>
      ) : null}
      {result ? <Result result={result} copy={copy} onOpenChecklist={onOpenChecklist} /> : null}
    </section>
  )
}

function Result({
  result,
  copy,
  onOpenChecklist,
}: {
  result: Calculation
  copy: Copy
  onOpenChecklist?: (templateId: string) => void
}) {
  const change = result.compared_to
  return (
    <div className="mt-6 rounded-2xl border border-rule bg-field px-5 py-5 shadow-[0_1px_2px_rgba(26,24,20,0.04),0_18px_40px_rgba(26,24,20,0.05)]">
      <p className="text-xs font-medium tracking-wide text-muted">{copy("calcTitle")}</p>
      <p className="num mt-1 font-statute text-4xl tracking-tight">{formatPkr(result.total_tax)}</p>
      <p className="mt-1 text-sm text-muted">
        {copy("effectiveRate")} {(result.effective_rate * 100).toFixed(2)}%
      </p>
      {change ? (
        <CompareBars
          leftLabel={result.tax_year}
          left={result.total_tax}
          rightLabel={change.tax_year}
          right={change.total_tax}
        />
      ) : null}
      {result.monthly_tax != null ? (
        <p className="mt-1 text-sm text-muted">
          {copy("monthlyTax")} {formatPkr(result.monthly_tax)}
        </p>
      ) : null}
      {result.net_annual != null ? (
        <p className="text-sm text-muted">
          {copy("netAnnual")} {formatPkr(result.net_annual)}
        </p>
      ) : null}
      <p className="mt-2 text-sm text-muted">
        {copy("rulesVersion")} {result.rules_version}
      </p>
      {change ? (
        <p className="mt-2 text-sm">
          {copy("yearChange")} {change.tax_year}: {formatPkr(change.difference)}
        </p>
      ) : null}
      {onOpenChecklist ? (
        <button
          type="button"
          onClick={() => onOpenChecklist("ntn_individual")}
          className={`${secondary} mt-3`}
        >
          {copy("becomeFiler")}
        </button>
      ) : null}
      <ul className="mt-3 grid gap-2 text-sm">
        {result.breakdown.map((line) => (
          <li key={line.label}>
            <p>{line.label}</p>
            <p className="text-muted">
              {formatPkr(line.tax)}. {line.source.law}. {line.source.ref}
            </p>
          </li>
        ))}
      </ul>
      {result.notes.map((note) => (
        <p key={note} className="mt-2 max-w-[68ch] text-sm text-muted">
          {note}
        </p>
      ))}
    </div>
  )
}
