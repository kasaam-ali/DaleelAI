/** Main nav items, page titles and the sidebar filing summary. */

import { FILERS, PROVINCES, TAXPAYERS, labelFor } from "../features/home/filing"
import type { CopyKey } from "../i18n"
import type { AppView } from "../lib/hashRoute"
import { filingCount, filingReady, type ClientTaxYear, type Profile } from "../lib/session"
import type { IconName } from "./icons"

type Copy = (key: CopyKey) => string

/** The main nav is exactly these four (SPEC PR 3). Other views stay reachable by deep link. */
export const NAV: { id: AppView; label: CopyKey; short: CopyKey; icon: IconName; group?: "tools" }[] = [
  { id: "home", label: "navHome", short: "railHome", icon: "home" },
  { id: "chat", label: "navAsk", short: "railAsk", icon: "chat", group: "tools" },
  { id: "calculator", label: "navCalcTool", short: "railCalc", icon: "calc", group: "tools" },
  { id: "notice", label: "navNoticeTool", short: "railNotice", icon: "notice", group: "tools" },
]

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

