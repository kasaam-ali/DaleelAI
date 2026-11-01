/** Site-wide credit band: affiliation disclaimer + "Made by". */

import type { CopyKey } from "../i18n"

export default function AppFooter({ copy, variant = "site" }: { copy: (key: CopyKey) => string; variant?: "site" }) {
  return (
    <footer className="site-footer" data-variant={variant}>
      <p className="site-footer-disclaimer">{copy("siteFooterDisclaimer")}</p>
      <p className="site-footer-credit">{copy("siteFooterCredit")}</p>
    </footer>
  )
}
