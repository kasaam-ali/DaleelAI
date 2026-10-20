/** The "Jump to latest" pill shown when the reader has scrolled up during an answer. */

import Icon from "../../../shell/icons"
import type { Copy } from "./types"

export default function JumpToLatest({ copy, onClick }: { copy: Copy; onClick: () => void }) {
  return (
    <button type="button" className="jump" onClick={onClick}>
      <span className="dot2" aria-hidden="true" />
      {copy("jumpLatest")}
      <Icon name="chev" size="sm" />
    </button>
  )
}
