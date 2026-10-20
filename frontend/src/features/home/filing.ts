/** Filing field options and the small helpers Home and the sidebar share. */

import type { CopyKey } from "../../i18n"
import type { ClientTaxYear, FilerStatus, Profile, Province, TaxpayerType } from "../../lib/session"
import { prefersReducedMotion } from "./useReducedMotion"

type Copy = (key: CopyKey) => string

export const FILERS: { value: FilerStatus; label: CopyKey }[] = [
  { value: "filer", label: "fsFilerOpt" },
  { value: "non_filer", label: "fsNonFilerOpt" },
  { value: "unknown", label: "fsNotSureOpt" },
]

export const TAXPAYERS: { value: TaxpayerType; label: CopyKey }[] = [
  { value: "salaried", label: "salaried" },
  { value: "freelancer", label: "freelancer" },
  { value: "business", label: "business" },
  { value: "company", label: "company" },
]

export const PROVINCES: { value: Province; label: CopyKey }[] = [
  { value: "punjab", label: "punjab" },
  { value: "sindh", label: "sindh" },
  { value: "kpk", label: "kpk" },
  { value: "balochistan", label: "balochistan" },
  { value: "islamabad", label: "islamabad" },
  { value: "gb", label: "gb" },
  { value: "ajk", label: "ajk" },
]

export const TAX_YEARS: ClientTaxYear[] = ["TY2026", "TY2027"]

export function labelFor<T extends string>(list: { value: T; label: CopyKey }[], value: T | null, copy: Copy) {
  const found = list.find((item) => item.value === value)
  return found ? copy(found.label) : ""
}

export const LAUNCH_MS = 520

/** Card → tool: a layer grows from the card into the content column (FLIP, transform only), then the route changes. */
export function launchFromCard(card: HTMLElement, open: () => void) {
  const column = card.closest("main")
  if (prefersReducedMotion() || !column) {
    open()
    return
  }
  const from = card.getBoundingClientRect()
  const col = column.getBoundingClientRect()
  const to = { left: col.left + 16, top: col.top + 16, width: col.width - 32, height: window.innerHeight - col.top - 32 }
  const layer = document.createElement("div")
  layer.className = "launch-layer"
  Object.assign(layer.style, { left: `${to.left}px`, top: `${to.top}px`, width: `${to.width}px`, height: `${to.height}px` })
  layer.style.transform = `translate(${from.left - to.left}px,${from.top - to.top}px) scale(${from.width / to.width},${from.height / to.height})`
  document.body.appendChild(layer)
  card.style.opacity = "0"
  requestAnimationFrame(() =>
    requestAnimationFrame(() => {
      layer.style.transition = "transform 460ms var(--ease-out)"
      layer.style.transform = "none"
    }),
  )
  window.setTimeout(() => {
    open()
    layer.style.transition = "opacity 240ms var(--ease-out)"
    layer.style.opacity = "0"
    window.setTimeout(() => layer.remove(), 260)
  }, LAUNCH_MS)
}

export function tunedEyebrow(profile: Profile, taxYear: ClientTaxYear, copy: Copy): string {
  const status = profile.filer_status === "unknown" ? "" : labelFor(FILERS, profile.filer_status, copy).toLowerCase()
  const type = labelFor(TAXPAYERS, profile.taxpayer_type, copy).toLowerCase()
  const province = labelFor(PROVINCES, profile.province, copy)
  const template = province ? copy("heroTuned") : copy("heroTunedNoProvince")
  return template
    .replace("{status}", status)
    .replace("{type}", type)
    .replace("{province}", province)
    .replace("{year}", taxYear)
    .replace(/\s+/g, " ")
    .trim()
}
