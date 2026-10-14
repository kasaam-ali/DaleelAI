export function widthPercent(value: number, other: number): number {
  const max = Math.max(value, other, 1)
  return Math.round((Math.max(value, 0) / max) * 100)
}
