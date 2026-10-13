import { useQuery } from '@tanstack/react-query'
import { getJson } from './client'

export type Health = {
  status: 'ok'
  version: string
  env: string
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => getJson<Health>('/health'),
    retry: 1,
  })
}
