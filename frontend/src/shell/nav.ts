/** Main nav items, page titles and the sidebar filing summary. */

import { FILERS, PROVINCES, TAXPAYERS, labelFor } from "../features/home/filing"
import type { CopyKey } from "../i18n"
import type { AppView } from "../lib/hashRoute"
import { filingCount, filingReady, type ClientTaxYear, type Profile } from "../lib/session"
import type { IconName } from "./icons"

type Copy = (key: CopyKey) => string

/** Nav v2 tools nav, in this order (handoff-pr18-nav.md §1). Each item is a real link to its hash route. */
export type ToolId = "home" | "ask" | "calc" | "notice" | "checklists" | "about"
export const TOOLS: { id: ToolId; view: AppView; href: string; label: CopyKey; short: CopyKey; icon: IconName }[] = [
  { id: "home", view: "home", href: "#/", label: "navHome", short: "railHome", icon: "home" },
  { id: "ask", view: "chat", href: "#/chat/new", label: "nvAsk", short: "nvAskShort", icon: "chat" },
  { id: "calc", view: "calculator", href: "#/calculator", label: "nvCalc", short: "railCalc", icon: "calc" },
  { id: "notice", view: "notice", href: "#/notice", label: "nvNotice", short: "railNotice", icon: "notice" },
  { id: "checklists", view: "checklist", href: "#/checklists", label: "nvChecklists", short: "nvListsShort", icon: "listck" },
  { id: "about", view: "privacy", href: "#/about", label: "navAbout", short: "railAbout", icon: "gear" },
]

/** Which tools-nav item is current for a view; deep links mark their parent. */
export function activeTool(view: AppView): ToolId {
  switch (view) {
    case "chat":
      return "ask"
    case "calculator":
    case "filer":
      return "calc"
    case "notice":
    case "experts":
      return "notice"
    case "checklist":
      return "checklists"
    case "updates":
    case "evaluation":
    case "privacy":
      return "about"
    default:
      return "home"
  }
}

export const TITLES: Partial<Record<AppView, CopyKey>> = {
  home: "navHome",
  calculator: "navCalcTool",
  notice: "navNoticeTool",
  filer: "navFiler",
  checklist: "navChecklist",
  experts: "navExperts",
  updates: "navUpdates",
  evaluation: "navEvaluation",
  privacy: "navAbout",
}

export function filingSummary(profile: Profile, taxYear: ClientTaxYear, taxYearSet: boolean, saved: boolean, copy: Copy): string {
  const count = filingCount(profile, taxYearSet)
  if (saved && filingReady(profile)) {
    return [
      labelFor(TAXPAYERS, profile.taxpayer_type, copy),
      labelFor(FILERS, profile.filer_status, copy),
      labelFor(PROVINCES, profile.province, copy),
      taxYear,
    ]
      .filter(Boolean)
      .join(" · ")
  }
  return count === 0 ? copy("filingNotSet") : copy("filingSomeSet").replace("{n}", String(count))
}

