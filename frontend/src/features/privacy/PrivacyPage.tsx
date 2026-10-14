import type { CopyKey } from "../../i18n"

type Copy = (key: CopyKey) => string

export default function PrivacyPage({ copy }: { copy: Copy }) {
  return (
    <section className="mt-8">
      <h2 className="font-statute text-3xl">{copy("privacyTitle")}</h2>
      <div className="mt-4 grid max-w-[62ch] gap-4 text-sm leading-6">
        <p>{copy("privacyAccounts")}</p>
        <p>{copy("privacyPii")}</p>
        <p>{copy("privacySources")}</p>
        <p>{copy("privacyExperts")}</p>
        <p>{copy("privacyWeb")}</p>
      </div>
    </section>
  )
}
