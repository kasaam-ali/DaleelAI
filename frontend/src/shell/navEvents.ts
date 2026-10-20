/** Non-component helpers shared by the sidebars. */

import type { MouseEvent } from "react"
import type { CopyKey } from "../i18n"

type Copy = (key: CopyKey) => string
export type Service = "checking" | "online" | "degraded" | "offline"

/** Plain left click routes in-app; modified clicks keep the browser default (new tab etc.). */
export function inAppClick(event: MouseEvent<HTMLAnchorElement>, go: () => void) {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  go()
}

export function statusText(service: Service, copy: Copy): string {
  return service === "online"
    ? copy("serviceOnline")
    : service === "offline"
      ? copy("serviceUnreachable")
      : service === "degraded"
        ? copy("serviceDegraded")
        : copy("serviceChecking")
}
