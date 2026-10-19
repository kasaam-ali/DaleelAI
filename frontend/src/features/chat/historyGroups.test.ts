/** Checks Today, Yesterday, Previous 7 days, and month groups. */

import { describe, expect, it } from "vitest"
import type { ChatSummary } from "../../api/chat"
import { groupChats, historyLabel } from "./historyGroups"

const labels = { today: "Today", yesterday: "Yesterday", week: "Previous 7 days" }
const now = new Date("2026-10-19T08:00:00Z")

function chat(id: string, updated_at: string): ChatSummary {
  return { id, title: id, created_at: updated_at, updated_at }
}

describe("history groups", () => {
  it("labels a Karachi calendar day", () => {
    expect(historyLabel("2026-10-19T02:00:00Z", now, labels)).toBe("Today")
    expect(historyLabel("2026-10-18T18:00:00Z", now, labels)).toBe("Yesterday")
    expect(historyLabel("2026-10-14T08:00:00Z", now, labels)).toBe("Previous 7 days")
    expect(historyLabel("2026-10-11T08:00:00Z", now, labels)).toBe("October")
    expect(historyLabel("2026-09-10T08:00:00Z", now, labels)).toBe("September")
  })

  it("keeps newest chats first inside each group", () => {
    const groups = groupChats(
      [
        chat("old", "2026-09-10T08:00:00Z"),
        chat("week", "2026-10-14T08:00:00Z"),
        chat("today-early", "2026-10-19T02:00:00Z"),
        chat("today-late", "2026-10-19T09:00:00Z"),
        chat("yesterday", "2026-10-18T18:00:00Z"),
      ],
      now,
      labels,
    )
    expect(groups.map((group) => group.label)).toEqual(["Today", "Yesterday", "Previous 7 days", "September"])
    expect(groups[0]?.chats.map((item) => item.id)).toEqual(["today-late", "today-early"])
  })
})
