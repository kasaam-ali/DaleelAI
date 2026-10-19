/** What chat shows before the first question. */

import type { CopyKey } from "../../i18n"

type Copy = (key: CopyKey) => string

export default function EmptyState({ copy }: { copy: Copy }) {
  return (
    <div className="max-w-[40rem] py-6">
      <h2 className="font-statute text-3xl leading-tight font-medium tracking-tight text-ink">
        {copy("emptyGreeting")}
      </h2>
      <p className="mt-3 text-base leading-relaxed text-muted">{copy("emptyHelp")}</p>
    </div>
  )
}
