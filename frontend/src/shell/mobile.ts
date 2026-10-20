/** Phone helpers (SPEC §10.1, PR M1): the phone breakpoint, the session-only disclaimer dismissal, and the keyboard inset. */

import { useEffect, useState } from "react"

export const PHONE_QUERY = "(max-width: 767px)"
export const DISC_KEY = "daleelai.discHidden"

export function readDiscHidden(): boolean {
  try {
    return sessionStorage.getItem(DISC_KEY) === "1"
  } catch {
    return false
  }
}

export function writeDiscHidden(): void {
  try {
    sessionStorage.setItem(DISC_KEY, "1")
  } catch {
    // Private mode: the banner just stays hidden until reload.
  }
}

function matches(query: string): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(query).matches
}

/** True at phone widths (≤767px); follows resizes. */
export function usePhone(): boolean {
  const [phone, setPhone] = useState(() => matches(PHONE_QUERY))
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return
    const mq = window.matchMedia(PHONE_QUERY)
    const on = () => setPhone(mq.matches)
    on()
    mq.addEventListener("change", on)
    return () => mq.removeEventListener("change", on)
  }, [])
  return phone
}

/** Keeps `--kb` on <html> equal to the on-screen keyboard height (iOS Safari), so the composer stays above it. */
export function useKeyboardInset(): void {
  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return
    const set = () =>
      document.documentElement.style.setProperty("--kb", `${Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop))}px`)
    set()
    vv.addEventListener("resize", set)
    vv.addEventListener("scroll", set)
    return () => {
      vv.removeEventListener("resize", set)
      vv.removeEventListener("scroll", set)
    }
  }, [])
}
