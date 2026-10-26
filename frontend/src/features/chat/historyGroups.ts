/** Groups saved chats the way the sidebar shows them. */

import type { ChatSummary } from "../../api/chat"

const ZONE = "Asia/Karachi"

export function clockNow(): Date {
  return new Date()
}

export type HistoryLabels = {
  today: string
  yesterday: string
  week: string
}

export type HistoryGroup = {
  id: string
  label: string
  chats: ChatSummary[]
}

function karachiDate(date: Date) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date)
  const read = (type: string) => Number(parts.find((part) => part.type === type)?.value ?? "0")
  return { year: read("year"), month: read("month"), day: read("day") }
}

function dayIndex(date: Date) {
  const { year, month, day } = karachiDate(date)
  return Math.floor(Date.UTC(year, month - 1, day) / 86_400_000)
}

export function historyLabel(iso: string, now: Date, labels: HistoryLabels): string {
  const when = new Date(iso)
  if (Number.isNaN(when.getTime())) return labels.today
  const delta = dayIndex(now) - dayIndex(when)
  if (delta <= 0) return labels.today
  if (delta === 1) return labels.yesterday
  if (delta <= 7) return labels.week
  return new Intl.DateTimeFormat("en-GB", { timeZone: ZONE, month: "long" }).format(when)
}

export function groupChats(chats: ChatSummary[], now: Date, labels: HistoryLabels): HistoryGroup[] {
  const sorted = [...chats].sort((a, b) => (a.updated_at < b.updated_at ? 1 : a.updated_at > b.updated_at ? -1 : 0))
  const groups: HistoryGroup[] = []
  const index = new Map<string, HistoryGroup>()
  for (const chat of sorted) {
    const label = historyLabel(chat.updated_at, now, labels)
    const when = new Date(chat.updated_at)
    const parts = Number.isNaN(when.getTime()) ? null : karachiDate(when)
    const id =
      label === labels.today
        ? "today"
        : label === labels.yesterday
          ? "yesterday"
          : label === labels.week
            ? "week"
            : parts
              ? `${parts.year}-${parts.month}`
              : label
    let group = index.get(id)
    if (!group) {
      group = { id, label, chats: [] }
      index.set(id, group)
      groups.push(group)
    }
    group.chats.push(chat)
  }
  return groups
}
