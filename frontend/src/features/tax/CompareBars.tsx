import { formatPkr } from "../../lib/money"
import { widthPercent } from "./bars"

export function CompareBars({
  leftLabel,
  left,
  rightLabel,
  right,
}: {
  leftLabel: string
  left: number
  rightLabel: string
  right: number
}) {
  return (
    <div className="mt-4 grid gap-2">
      <Bar label={leftLabel} value={left} width={widthPercent(left, right)} />
      <Bar label={rightLabel} value={right} width={widthPercent(right, left)} />
    </div>
  )
}

function Bar({ label, value, width }: { label: string; value: number; width: number }) {
  return (
    <div>
      <p className="text-sm">
        {label} {formatPkr(value)}
      </p>
      <div className="mt-1 h-3 border border-rule bg-paper">
        <div className="h-full bg-seal" style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}
