/** Checklist list and detail calls stay on the session. */

// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from "vitest"
import { getChecklist, listChecklists } from "./phase5"

const SESSION = "11111111-1111-4111-8111-111111111111"

describe("checklist reads", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it("lists and gets with the session header", async () => {
    localStorage.setItem("daleelai.session_id", SESSION)
    const checklist = {
      id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      template_id: "ntn_individual",
      title: "NTN registration",
      steps: [],
      progress: 0,
    }
    const fetchMock = vi.fn(async (url: string) => {
      const body = String(url).endsWith("/checklists") ? [checklist] : checklist
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    })
    vi.stubGlobal("fetch", fetchMock)

    const rows = await listChecklists()
    expect(rows).toEqual([checklist])
    const found = await getChecklist(checklist.id)
    expect(found.title).toBe("NTN registration")

    const listCall = fetchMock.mock.calls[0]
    const getCall = fetchMock.mock.calls[1]
    if (!listCall || !getCall) throw new Error("missing fetch call")
    expect(String(listCall[0])).toContain("/api/v1/checklists")
    expect((listCall[1] as RequestInit).headers).toEqual({ "X-Session-Id": SESSION })
    expect(String(getCall[0])).toContain(`/api/v1/checklists/${checklist.id}`)
    expect((getCall[1] as RequestInit).method).toBe("GET")
    expect(((getCall[1] as RequestInit).headers as Record<string, string>)["X-Session-Id"]).toBe(SESSION)
  })

  it("surfaces the app error message", async () => {
    localStorage.setItem("daleelai.session_id", SESSION)
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              error: { code: "not_found", message: "That checklist was not found." },
            }),
            { status: 404 },
          ),
      ),
    )
    await expect(getChecklist("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")).rejects.toThrow(
      "That checklist was not found.",
    )
  })
})
