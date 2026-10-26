/** A short confirmation toast ("Copied with sources", "Link copied"). */

import Icon from "../../../shell/icons"

export default function Toast({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div className="toast2" role="status">
      <Icon name="check" size="sm" />
      {message}
    </div>
  )
}
