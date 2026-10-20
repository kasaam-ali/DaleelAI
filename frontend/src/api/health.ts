/** Reads /health so the shell can show whether the API is up. */

import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { getJson } from "./client"

export type DependencyCheck = {
  status: "ok" | "slow" | "down"
  latency_ms: number
}

export type Health = {
  status: "ok" | "degraded"
  version: string
  env: string
  corpus_version: string
  corpus_date?: string
  supported_tax_years: string[]
  models: Record<string, string>
  checks?: {
    api: DependencyCheck
    qdrant: DependencyCheck
    postgres: DependencyCheck
    llm: DependencyCheck
    embeddings: DependencyCheck
  }
}

export type ServiceState = "checking" | "online" | "degraded" | "offline"

export function serviceState(
  online: boolean,
  health: { error: boolean; ok: boolean; status?: string | null },
): ServiceState {
  if (!online) return "offline"
  if (health.error || (health.ok && health.status === "degraded")) return "degraded"
  if (health.ok) return "online"
  return "checking"
}

export function useBrowserOnline() {
  const [online, setOnline] = useState(() => navigator.onLine)
  useEffect(() => {
    function sync() {
      setOnline(navigator.onLine)
    }
    window.addEventListener("online", sync)
    window.addEventListener("offline", sync)
    return () => {
      window.removeEventListener("online", sync)
      window.removeEventListener("offline", sync)
    }
  }, [])
  return online
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => getJson<Health>("/health", signal),
    retry: 1,
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  })
}
