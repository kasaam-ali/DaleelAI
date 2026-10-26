/** Shown under the header while the browser is offline. */

import type { CopyKey } from "../../i18n"

type Copy = (key: CopyKey) => string

export default function OfflineBanner({ queuedCount, copy }: { queuedCount: number; copy: Copy }) {
  return (
    <p data-motion-slot="offline-banner" role="status" className="border-b border-rule bg-elevated px-4 py-2 text-sm text-warning">
      {copy("offlineBanner")}
      {queuedCount > 0 ? ` (${queuedCount})` : ""}
    </p>
  )
}
