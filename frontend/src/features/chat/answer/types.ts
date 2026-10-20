/** Shared props for the answer view. */

import type { CopyKey } from "../../../i18n"

export type Copy = (key: CopyKey) => string

/** Which source panel is open, for which turn, and whether it shows the law view. */
export type PanelState = { turnId: string; n: number; law: boolean } | null

export type OpenSource = (n: number, opener: HTMLElement | null, law?: boolean) => void

export function panelId(turnId: string): string {
  return `src-panel-${turnId}`
}
