/** Offline banner under the top bar (SPEC §5.2A item 11, §6). Disappears when the browser is back online. */

import type { CopyKey } from "../../i18n"
import Icon from "../../shell/icons"

type Copy = (key: CopyKey) => string

export default function OfflineBanner({ queuedCount, copy }: { queuedCount: number; copy: Copy }) {
  return (
    <div data-motion-slot="offline-banner" role="status" className="offline-bar">
      <Icon name="wifiOff" />
      <span>
        <b>{copy("offlineTitle")}</b> {copy("offlineBody")}
        {queuedCount > 0 ? ` (${queuedCount})` : ""}
      </span>
    </div>
  )
}
