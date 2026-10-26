/** Says what is stored, what is hidden, and where answers come from. */

import type { CopyKey } from "../../i18n"

type Copy = (key: CopyKey) => string

export default function PrivacyPage({
  copy,
  onClearHistory,
}: {
  copy: Copy
  onClearHistory: () => void
}) {
  return (
    <section>
      <h2 className="page-title">{copy("privacyTitle")}</h2>
      <div className="panel mt-4 grid max-w-[68ch] gap-4 px-4 py-4 text-sm leading-6">
        <p>{copy("privacyAccounts")}</p>
        <p>{copy("privacyPii")}</p>
        <p>{copy("privacySources")}</p>
        <p>{copy("privacyExperts")}</p>
        <p>{copy("privacyWeb")}</p>
      </div>
      <button
        type="button"
        onClick={onClearHistory}
        className="mt-6 min-h-11 rounded-full border border-rule px-4 text-sm hover:bg-elevated"
      >
        {copy("clearHistory")}
      </button>
    </section>
  )
}
