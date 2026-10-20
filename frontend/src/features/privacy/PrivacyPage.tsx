/** Says what is stored, what is hidden, and where answers come from. */

import { useState } from "react"
import type { CopyKey } from "../../i18n"
import ConfirmDialog from "../../shell/ConfirmDialog"

type Copy = (key: CopyKey) => string

export default function PrivacyPage({
  copy,
  onClearHistory,
  clearError = null,
}: {
  copy: Copy
  onClearHistory: () => void
  clearError?: string | null
}) {
  const [confirming, setConfirming] = useState(false)
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
      <section aria-labelledby="your-data" className="mt-8 max-w-[68ch]">
        <h3 id="your-data" className="text-base font-semibold">
          {copy("dataTitle")}
        </h3>
        <div className="panel mt-3 flex flex-wrap items-start gap-4 px-4 py-4">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">{copy("dataClearTitle")}</p>
            <p className="mt-1 text-sm text-muted">{copy("dataClearBody")}</p>
            <ul className="mt-2 flex flex-wrap gap-1.5" aria-label={copy("dataClearTitle")}>
              {(["dataClearWhat1", "dataClearWhat2"] as const).map((key) => (
                <li key={key} className="rounded-md bg-elevated px-2 py-0.5 text-xs text-muted">
                  {copy(key)}
                </li>
              ))}
            </ul>
          </div>
          <button
            type="button"
            data-clear-history
            onClick={() => setConfirming(true)}
            className="min-h-11 rounded-lg border border-rule px-4 text-sm hover:bg-elevated"
          >
            {copy("dataClearAction")}
          </button>
        </div>
        {clearError ? <p className="mt-3 text-sm text-low" role="alert">{clearError}</p> : null}
      </section>
      {confirming ? (
        <ConfirmDialog
          title={copy("dataDlgTitle")}
          body={
            <>
              {copy("dataDlgBody")}
              <span className="mt-2 block">• {copy("dataDlgList")}</span>
              <span className="mt-2 block text-ink">{copy("dataDlgNote")}</span>
            </>
          }
          cancelLabel={copy("dataDlgCancel")}
          confirmLabel={copy("dataDlgConfirm")}
          onCancel={() => setConfirming(false)}
          onConfirm={() => {
            setConfirming(false)
            onClearHistory()
          }}
        />
      ) : null}
    </section>
  )
}
