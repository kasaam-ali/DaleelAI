/** True when the device asks for reduced motion. JS motion (tilt, launch) checks this. */

import { useEffect, useState } from "react"

const QUERY = "(prefers-reduced-motion: reduce)"

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(QUERY).matches
}

export function useReducedMotion(): boolean {
  const [reduce, setReduce] = useState(prefersReducedMotion)
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return
    const list = window.matchMedia(QUERY)
    const onChange = () => setReduce(list.matches)
    list.addEventListener?.("change", onChange)
    return () => list.removeEventListener?.("change", onChange)
  }, [])
  return reduce
}
