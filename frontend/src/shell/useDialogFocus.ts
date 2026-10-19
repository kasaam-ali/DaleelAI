/** Keeps Tab inside an open dialog and closes it on Escape. */

import { useEffect, useRef, type RefObject } from "react"

function focusable(root: HTMLElement | null) {
  return Array.from(root?.querySelectorAll<HTMLElement>("button, a, input, select, textarea") ?? []).filter(
    (element) => !element.hasAttribute("disabled") && element.tabIndex !== -1,
  )
}

export function useDialogFocus(open: boolean, ref: RefObject<HTMLElement | null>, onEscape: () => void) {
  const escapeRef = useRef(onEscape)

  useEffect(() => {
    escapeRef.current = onEscape
  }, [onEscape])

  useEffect(() => {
    if (!open) return
    focusable(ref.current)[0]?.focus()

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault()
        event.stopPropagation()
        escapeRef.current()
        return
      }
      if (event.key !== "Tab") return
      const items = focusable(ref.current)
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }

    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [open, ref])
}
