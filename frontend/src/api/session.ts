/** Deletes the anonymous session's stored chats. */

import { API_URL } from "./client"

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/session`, {
    method: "DELETE",
    headers: { "X-Session-Id": sessionId },
  })
  if (response.status === 204) return
  let message = `Request failed (${response.status})`
  try {
    const body = (await response.json()) as { error?: { message?: string } }
    if (body.error?.message) message = body.error.message
  } catch {
    /* the body was not JSON */
  }
  throw new Error(message)
}
