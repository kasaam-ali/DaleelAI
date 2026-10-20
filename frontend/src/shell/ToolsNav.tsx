/** Tools nav on Home and every tool page: the 6 links, then Filing + status (handoff-pr18-nav.md §3). */

import type { CopyKey } from "../i18n"
import type { AppView } from "../lib/hashRoute"
import NavLink from "./NavLink"
import Icon from "./icons"
import { TOOLS, activeTool, type ToolId } from "./nav"

type Copy = (key: CopyKey) => string

export default function ToolsNav({ view, copy, onTool }: { view: AppView; copy: Copy; onTool: (id: ToolId) => void }) {
  const active = activeTool(view)
  return (
    <nav aria-label={copy("navTools")} className="tools-nav" data-tools-nav>
      {TOOLS.map((item) => (
        <NavLink
          key={item.id}
          href={item.href}
          title={copy(item.label)}
          current={active === item.id}
          className={`nav-item keep${active === item.id ? " on" : ""}`}
          onGo={() => onTool(item.id)}
        >
          <Icon name={item.icon} />
          <span className="lbl">{copy(item.label)}</span>
          <span className="short" aria-hidden="true">
            {copy(item.short)}
          </span>
        </NavLink>
      ))}
    </nav>
  )
}
