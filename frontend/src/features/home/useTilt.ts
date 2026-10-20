/** Pointer tilt (max 6°) and glare position for a card. Off for reduced motion and coarse pointers. */

import { useEffect, type RefObject } from "react"
import { prefersReducedMotion } from "./useReducedMotion"

export const MAX_TILT = 6

/** Rotation for a pointer at (x, y), each 0..1 across the card. */
export function tiltFor(x: number, y: number): { rotateX: number; rotateY: number } {
  const clamp = (value: number) => Math.min(1, Math.max(0, value))
  return { rotateX: (0.5 - clamp(y)) * MAX_TILT * 2, rotateY: (clamp(x) - 0.5) * MAX_TILT * 2 }
}

function finePointer(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(pointer: fine)").matches
}

export function useTilt(card: RefObject<HTMLElement | null>, inner: RefObject<HTMLElement | null>, enabled = true): void {
  useEffect(() => {
    const root = card.current
    const target = inner.current
    if (!enabled || !root || !target || prefersReducedMotion() || !finePointer()) return
    let frame = 0
    function onMove(event: PointerEvent) {
      if (!root || !target) return
      const rect = root.getBoundingClientRect()
      const x = rect.width ? (event.clientX - rect.left) / rect.width : 0.5
      const y = rect.height ? (event.clientY - rect.top) / rect.height : 0.5
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const { rotateX, rotateY } = tiltFor(x, y)
        target.style.transition = "transform 80ms linear"
        target.style.transform = `perspective(900px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateZ(0)`
        root.style.setProperty("--gx", `${(x * 100).toFixed(1)}%`)
        root.style.setProperty("--gy", `${(y * 100).toFixed(1)}%`)
      })
    }
    function onLeave() {
      if (!target) return
      cancelAnimationFrame(frame)
      target.style.transition = "transform 600ms var(--ease-spring)"
      target.style.transform = ""
    }
    root.addEventListener("pointermove", onMove)
    root.addEventListener("pointerleave", onLeave)
    return () => {
      cancelAnimationFrame(frame)
      root.removeEventListener("pointermove", onMove)
      root.removeEventListener("pointerleave", onLeave)
    }
  }, [card, inner, enabled])
}
