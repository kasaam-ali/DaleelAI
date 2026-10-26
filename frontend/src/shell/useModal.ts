/** Shared dialog and sheet behaviour: focus moves in, the rest of the page is inert, Tab is trapped, Esc closes, focus returns. */

import { useEffect, useRef, type RefObject } from "react"

const FOCUSABLE = "button, a[href], input, select, textarea, [tabindex]"

function focusables(root: HTMLElement | null): HTMLElement[] {
  return Array.from(root?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []).filter(
    (element) => !element.hasAttribute("disabled") && element.tabIndex !== -1,
  )
}

/** Marks every element outside `root` inert by walking up and flagging siblings (a `data-modal-scrim` stays clickable). Returns an undo function. */
function inertOutside(root: HTMLElement): () => void {
  const marked: HTMLElement[] = []
  let node: HTMLElement = root
  while (node.parentElement && node !== document.body) {
    const parent: HTMLElement = node.parentElement
    for (const sibling of Array.from(parent.children)) {
      if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert && sibling.tagName !== "SCRIPT" && !sibling.hasAttribute("data-modal-scrim")) {
        sibling.inert = true
        marked.push(sibling)
      }
    }
    node = parent
  }
  return () => {
    for (const element of marked) element.inert = false
  }
}

export function useModal(open: boolean, ref: RefObject<HTMLElement | null>, onClose: () => void) {
  const closeRef = useRef(onClose)

  useEffect(() => {
    closeRef.current = onClose
  }, [onClose])

  useEffect(() => {
    const root = ref.current
    if (!open || !root) return
    const returnTo = document.activeElement instanceof HTMLElement ? document.activeElement : null
    ;(focusables(root)[0] ?? root).focus()
    const undoInert = inertOutside(root)

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault()
        event.stopPropagation()
        closeRef.current()
        return
      }
      if (event.key !== "Tab") return
      const items = focusables(ref.current)
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("keydown", onKey)
      undoInert()
      if (returnTo?.isConnected) returnTo.focus()
    }
  }, [open, ref])
}
