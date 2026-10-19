import type { CopyKey } from "../../i18n"

type Copy = (key: CopyKey) => string

export default function PrivacyPage({ copy }: { copy: Copy }) {
  return (
    <section>
      <h2 className="font-statute text-3xl tracking-tight">{copy("privacyTitle")}</h2>
      <div className="mt-4 grid max-w-[62ch] gap-4 rounded-2xl border border-rule bg-field px-5 py-5 text-sm leading-6">
        <p>{copy("privacyAccounts")}</p>
        <p>{copy("privacyPii")}</p>
        <p>{copy("privacySources")}</p>
        <p>{copy("privacyExperts")}</p>
        <p>{copy("privacyWeb")}</p>
      </div>
    </section>
  )
}
