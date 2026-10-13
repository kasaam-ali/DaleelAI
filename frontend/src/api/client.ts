export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`)
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`)
  }
  return (await response.json()) as T
}
