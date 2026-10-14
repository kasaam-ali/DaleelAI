import { API_URL } from "./client"
import { readSessionId } from "../lib/session"

export type NoticeExplanation = {
  notice_type: string
  law: string
  section: string | null
  tax_year: string | null
  amount: number | null
  deadline: string | null
  issuing_office: string | null
  explanation: {
    summary: string
    why_received: string
    next_steps: string[]
    severity: "low" | "medium" | "high"
    recommend_expert: boolean
    days_left: number | null
  }
  sources: { title: string; section: string | null; snippet: string }[]
  redactions: Record<string, number>
  ocr_used: boolean
  action_links: { label: string; label_ru: string; url: string; authority: string }[]
  classification: {
    category: string | null
    complexity: string
    confidence: number
    low_confidence: boolean
  } | null
  expert_category: string | null
}

export async function explainNotice(file: File, language: string): Promise<NoticeExplanation> {
  const body = new FormData()
  body.set("file", file)
  body.set("language", language)
  const response = await fetch(`${API_URL}/api/v1/notice/explain`, {
    method: "POST",
    body,
    signal: AbortSignal.timeout(20000),
  })
  const payload = (await response.json()) as NoticeExplanation & {
    error?: { message?: string }
  }
  if (!response.ok) {
    throw new Error(payload.error?.message ?? "notice failed")
  }
  return payload
}

export type ChecklistTemplate = {
  id: string
  title: string
  title_ru: string
  description: string
  questions: { id: string; prompt: string; prompt_ru: string; options: string[] }[]
}

export type Checklist = {
  id: string
  template_id: string
  title: string
  steps: {
    id: string
    title: string
    detail: string
    sources: string[]
    done: boolean
    link?: { label: string; url: string } | null
  }[]
  progress: number
}

export async function checklistTemplates(): Promise<ChecklistTemplate[]> {
  const response = await fetch(`${API_URL}/api/v1/checklists/templates`, {
    signal: AbortSignal.timeout(15000),
  })
  if (!response.ok) throw new Error("templates failed")
  return (await response.json()) as ChecklistTemplate[]
}

export async function startChecklist(
  templateId: string,
  answers: Record<string, string>,
  language: string,
): Promise<Checklist> {
  return checklistJson("/api/v1/checklists", {
    method: "POST",
    body: JSON.stringify({ template_id: templateId, answers, language }),
  })
}

export async function markChecklistStep(
  checklistId: string,
  stepId: string,
  done: boolean,
): Promise<Checklist> {
  return checklistJson(`/api/v1/checklists/${checklistId}/steps/${stepId}`, {
    method: "PATCH",
    body: JSON.stringify({ done }),
  })
}

async function checklistJson(path: string, init: RequestInit): Promise<Checklist> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": readSessionId(localStorage),
    },
    signal: AbortSignal.timeout(15000),
  })
  const payload = (await response.json()) as Checklist & { error?: { message?: string } }
  if (!response.ok) {
    throw new Error(payload.error?.message ?? "checklist failed")
  }
  return payload
}
