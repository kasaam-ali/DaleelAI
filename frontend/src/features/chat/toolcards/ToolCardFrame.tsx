/** The shared in-chat tool card frame (.ccard): header with icon + kind label + link, body, foot line. */

import type { ReactNode } from "react"
import Icon, { type IconName } from "../../../shell/icons"

export default function ToolCardFrame({
  icon,
  label,
  link,
  kind,
  children,
}: {
  icon: IconName
  label: string
  link?: { href: string; text: string } | null
  kind: string
  children: ReactNode
}) {
  return (
    <div className="card ccard" role="group" aria-label={label} data-tool-card={kind}>
      <div className="ch">
        <Icon name={icon} size="sm" />
        <span>{label}</span>
        {link ? (
          <a href={link.href}>
            {link.text}
            <Icon name="chev" size="sm" />
          </a>
        ) : null}
      </div>
      {children}
    </div>
  )
}

export function CardFoot({ icon, start, end }: { icon: IconName; start: ReactNode; end?: ReactNode }) {
  return (
    <div className="cf">
      <Icon name={icon} size="sm" />
      <span>{start}</span>
      <span className="sp" />
      {end ? <span>{end}</span> : null}
    </div>
  )
}
