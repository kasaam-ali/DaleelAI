/** A sidebar link: a real `<a href>` that routes in-app on a plain click (handoff-pr18-nav.md §3). */

import type { ReactNode } from "react"
import { inAppClick } from "./navEvents"

export default function NavLink({
  href,
  current,
  className,
  title,
  ariaLabel,
  onGo,
  children,
}: {
  href: string
  current?: boolean
  className: string
  title: string
  ariaLabel?: string
  onGo: () => void
  children: ReactNode
}) {
  return (
    <a
      href={href}
      title={title}
      aria-label={ariaLabel}
      aria-current={current ? "page" : undefined}
      className={className}
      onClick={(event) => inAppClick(event, onGo)}
    >
      {children}
    </a>
  )
}
