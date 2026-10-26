/** Finds a public expert and loads the classifier report. */

import { API_URL } from "./client"

export type ExpertFind = {
  classification: {
    category: string | null
    complexity: "simple" | "complex"
    confidence: number
    low_confidence: boolean
  }
  experts: {
    id: string
    name: string
    firm: string | null
    city: string
    specialties: string[]
    profile_url: string
    source: string
    last_updated: string
    match_score: number
  }[]
  advice: string
  advice_ru: string
  advice_code: "uncertain_category" | "simple_question" | "no_listing" | "ok"
  disclaimer: string
  removal_contact: string
  disclaimer_ru?: string
  removal_contact_ru?: string
}

export async function findExperts(
  query: string,
  city: string,
  category: string | null,
): Promise<ExpertFind> {
  const response = await fetch(`${API_URL}/api/v1/experts/find`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      city: city || null,
      category,
    }),
    signal: AbortSignal.timeout(15000),
  })
  const payload = (await response.json()) as ExpertFind & { error?: { message?: string } }
  if (!response.ok) throw new Error(payload.error?.message ?? "experts failed")
  return payload
}

export type ClassifierReport = {
  served_model: string
  candidates: {
    name: string
    human_test: Score
    synthetic_test: Score
  }[]
  not_trained: { name: string; reason: string }[]
}

type Score = {
  accuracy: number
  macro_f1: number
  per_language_f1: { en: number; roman_urdu: number }
  latency_ms_mean: number
  confusion_matrix: { labels: string[]; matrix: number[][] }
}

export type AblationStage = {
  name: string
  status: string
  recall_at_5: number | null
  coverage: number | null
  mean_latency_ms: number | null
  rows: number
  reason: string
}

export type AblationReport = {
  sample_size: number
  documents_unchanged: boolean
  dataset: {
    total: number
    en: number
    roman_urdu: number
    special: number
    dev: number
    test: number
  }
  stages: AblationStage[]
}

export async function ablationReport(): Promise<AblationReport> {
  const response = await fetch(`${API_URL}/api/v1/evaluation/ablation`, {
    signal: AbortSignal.timeout(15000),
  })
  if (!response.ok) throw new Error("missing")
  return (await response.json()) as AblationReport
}

export async function classifierReport(): Promise<ClassifierReport> {
  const response = await fetch(`${API_URL}/api/v1/evaluation/classifier`, {
    signal: AbortSignal.timeout(15000),
  })
  if (!response.ok) throw new Error("missing")
  return (await response.json()) as ClassifierReport
}
