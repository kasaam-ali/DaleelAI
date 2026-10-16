export type TurnBucket<T> = { id: string | null; turns: T[] }

export function reduceBucket<T>(
  current: TurnBucket<T>,
  update: T[] | ((turns: T[]) => T[]),
  selectedId: string | null,
  liveId: string | null,
): TurnBucket<T> {
  const continuing = current.id === selectedId || (liveId !== null && current.id === liveId)
  const base = continuing || (selectedId === null && current.id === null) ? current.turns : []
  const turns = typeof update === "function" ? update(base) : update
  const id = liveId ?? (selectedId === null && current.id !== null && !continuing ? null : (current.id ?? selectedId))
  return { id, turns }
}
