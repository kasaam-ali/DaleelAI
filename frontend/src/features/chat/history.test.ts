/** Reopened chats keep the law-as-of date and the sources on that answer. */

import { describe, expect, it } from "vitest"
import type { StoredMessage } from "../../api/chat"
import { turnsFromHistory } from "./history"

function message(patch: Partial<StoredMessage> & Pick<StoredMessage, "id" | "role" | "content">): StoredMessage {
  return {
    intent: "qa",
    language: "en",
    tax_year: "TY2027",
    sources: [],
    answer_source: patch.role === "assistant" ? "verified" : null,
    confidence: "high",
    verified: true,
    model: "demo",
    created_at: "2026-10-19T12:00:00.000Z",
    feedback: null,
    feedback_reason: null,
    ...patch,
  }
}

const source = {
  library: "verified" as const,
  doc_id: "ito",
  title: "Income Tax Ordinance",
  section: "149",
  page: 80,
  url: "https://example.test/149",
  mirror_url: null,
  site: null,
  fetched_at: null,
  snippet: "Salary withholding.",
  rerank_score: null,
}

describe("turnsFromHistory", () => {
  it("restores the law-as-of date remembered for that answer", () => {
    const turns = turnsFromHistory(
      [
        message({ id: "q1", role: "user", content: "What does section 149 cover?" }),
        message({ id: "a1", role: "assistant", content: "Section 149 covers salary." }),
      ],
      { a1: "2026-10-14" },
    )
    expect(turns).toHaveLength(1)
    expect(turns[0].final?.corpus_date).toBe("2026-10-14")
    expect(turns[0].final?.tax_year).toBe("TY2027")
  })

  it("keeps each source rail with its own question when timestamps tie", () => {
    const first = "2026-10-19T12:00:00.000Z"
    const second = "2026-10-19T12:01:00.000Z"
    const turns = turnsFromHistory(
      [
        message({
          id: "a1",
          role: "assistant",
          content: "First answer.",
          created_at: first,
          sources: [{ ...source, section: "149" }],
        }),
        message({ id: "q1", role: "user", content: "First question", created_at: first, answer_source: null }),
        message({
          id: "a2",
          role: "assistant",
          content: "Second answer.",
          created_at: second,
          sources: [{ ...source, section: "150", doc_id: "ito-150" }],
        }),
        message({ id: "q2", role: "user", content: "Second question", created_at: second, answer_source: null }),
      ],
      {},
    )
    expect(turns.map((turn) => turn.question)).toEqual(["First question", "Second question"])
    expect(turns.map((turn) => turn.sources[0]?.section)).toEqual(["149", "150"])
  })
})
