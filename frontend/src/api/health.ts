/** Reads /health so the shell can show whether the API is up. */

import { useQuery } from '@tanstack/react-query'
import { getJson } from './client'

export type Health = {
  status: 'ok'
  version: string
  env: string
  corpus_version: string
  supported_tax_years: string[]
  models: Record<string, string>
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => getJson<Health>('/health', signal),
    retry: 1,
  })
}
