/** Loads this session's chats and applies rename and delete to the query cache. */

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useCallback } from "react"
import { deleteChat, getChat, listChats, renameChat, type ChatSummary } from "../../api/chat"
import { assistantSnippet } from "./chatText"

export function chatsQueryKey(sessionId: string) {
  return ["chats", sessionId] as const
}

export function snippetsQueryKey(sessionId: string) {
  return ["chat-snippets", sessionId] as const
}

/** Sessions just created by "Clear chats": the server has nothing for them, so skip the GET until something changes. */
const emptySessions = new Set<string>()

export function useChatHistory(sessionId: string) {
  const queryClient = useQueryClient()
  const chatsQuery = useQuery({
    queryKey: chatsQueryKey(sessionId),
    queryFn: () => listChats(sessionId),
    retry: false,
    initialData: emptySessions.has(sessionId) ? [] : undefined,
    staleTime: emptySessions.has(sessionId) ? Infinity : 0,
  })
  const snippetQuery = useQuery({
    queryKey: snippetsQueryKey(sessionId),
    queryFn: async () => ({}) as Record<string, string>,
    initialData: {} as Record<string, string>,
    enabled: false,
    staleTime: Infinity,
  })

  const rememberSnippet = useCallback(
    (chatId: string, text: string) => {
      const snippet = text.replace(/\s+/g, " ").trim().slice(0, 180)
      if (!snippet) return
      queryClient.setQueryData<Record<string, string>>(snippetsQueryKey(sessionId), (current) => ({
        ...(current ?? {}),
        [chatId]: snippet,
      }))
    },
    [queryClient, sessionId],
  )

  const prefetchSnippets = useCallback(() => {
    const rows = queryClient.getQueryData<ChatSummary[]>(chatsQueryKey(sessionId)) ?? []
    const known = queryClient.getQueryData<Record<string, string>>(snippetsQueryKey(sessionId)) ?? {}
    const missing = rows.filter((row) => !known[row.id]).slice(0, 24)
    if (missing.length === 0) return
    void Promise.all(
      missing.map(async (row) => {
        try {
          const detail = await getChat(sessionId, row.id)
          return [row.id, assistantSnippet(detail.messages)] as const
        } catch {
          return [row.id, ""] as const
        }
      }),
    ).then((pairs) => {
      queryClient.setQueryData<Record<string, string>>(snippetsQueryKey(sessionId), (current) => {
        const next = { ...(current ?? {}) }
        for (const [id, snippet] of pairs) {
          if (snippet) next[id] = snippet
        }
        return next
      })
    })
  }, [queryClient, sessionId])

  const rename = useCallback(
    async (chatId: string, title: string) => {
      const key = chatsQueryKey(sessionId)
      const previous = queryClient.getQueryData<ChatSummary[]>(key)
      queryClient.setQueryData<ChatSummary[]>(key, (rows = []) =>
        rows.map((row) => (row.id === chatId ? { ...row, title } : row)),
      )
      try {
        const updated = await renameChat(sessionId, chatId, title)
        queryClient.setQueryData<ChatSummary[]>(key, (rows = []) =>
          rows.map((row) => (row.id === chatId ? { ...row, ...updated } : row)),
        )
      } catch (error) {
        queryClient.setQueryData(key, previous ?? [])
        throw error
      }
    },
    [queryClient, sessionId],
  )

  const remove = useCallback(
    async (chatId: string) => {
      await deleteChat(sessionId, chatId)
      const key = chatsQueryKey(sessionId)
      queryClient.setQueryData<ChatSummary[]>(key, (rows = []) => rows.filter((row) => row.id !== chatId))
      void queryClient.invalidateQueries({ queryKey: key })
    },
    [queryClient, sessionId],
  )

  /** Call before switching to a freshly cleared session: its list starts empty with no request. */
  const startEmpty = useCallback(
    (nextSessionId: string) => {
      emptySessions.add(nextSessionId)
      queryClient.setQueryData<ChatSummary[]>(chatsQueryKey(nextSessionId), [])
    },
    [queryClient],
  )

  const refresh = useCallback(() => {
    emptySessions.delete(sessionId)
    void queryClient.invalidateQueries({ queryKey: chatsQueryKey(sessionId) })
  }, [queryClient, sessionId])

  return {
    chats: chatsQuery.data ?? [],
    snippets: snippetQuery.data ?? {},
    rememberSnippet,
    prefetchSnippets,
    rename,
    remove,
    refresh,
    startEmpty,
  }
}
