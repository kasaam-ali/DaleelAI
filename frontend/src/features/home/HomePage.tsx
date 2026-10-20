/** Premium Home (SPEC §5.1): filing details, hero with the question box, three tool cards, and the trust row. */

import { useState, type CSSProperties } from "react"
import type { CopyKey } from "../../i18n"
import { filingReady, type ClientTaxYear, type Profile } from "../../lib/session"
import { redactPii } from "../../lib/pii"
import Composer from "../chat/Composer"
import OfflineBanner from "../chat/OfflineBanner"
import { useOnline } from "../chat/useOnline"
import Icon from "../../shell/icons"
import type { AppView } from "../../shell/AppShell"
import FilingStep from "./FilingStep"
import { launchFromCard, tunedEyebrow } from "./filing"
import { lawDateLabel } from "../../lib/lawDate"
import HeroEmblem from "./HeroEmblem"
import ToolCard, { type ToolArt } from "./ToolCard"
import "./home.css"

type Copy = (key: CopyKey) => string

const TOOLS: { view: AppView; art: ToolArt; icon: "chat" | "calc" | "notice"; n: 1 | 2 | 3 }[] = [
  { view: "chat", art: "ask", icon: "chat", n: 1 },
  { view: "calculator", art: "calc", icon: "calc", n: 2 },
  { view: "notice", art: "notice", icon: "notice", n: 3 },
]

const CHIPS = ["heroChip1", "heroChip2", "heroChip3"] as const

const TRUST = [
  ["trust1Title", "trust1Desc"],
  ["trust2Title", "trust2Desc"],
  ["trust3Title", "trust3Desc"],
] as const

export default function HomePage({
  copy,
  profile,
  taxYear,
  taxYearSet,
  filingSaved,
  onProfile,
  onTaxYear,
  onFilingSaved,
  onOpen,
  onAsk,
}: {
  copy: Copy
  profile: Profile
  taxYear: ClientTaxYear
  taxYearSet: boolean
  filingSaved: boolean
  onProfile: (patch: Partial<Profile>) => void
  onTaxYear: (taxYear: ClientTaxYear) => void
  onFilingSaved: (saved: boolean) => void
  onOpen: (view: AppView) => void
  onAsk: (question: string) => void
}) {
  const [draft, setDraft] = useState("")
  const online = useOnline()
  const [error, setError] = useState<string | null>(null)
  const preview = redactPii(draft)
  const showPreview = draft.trim().length > 0 && preview !== draft
  const saved = filingSaved && filingReady(profile)

  function submit() {
    const question = draft.trim()
    if (!question) {
      setError(copy("writeQuestion"))
      return
    }
    setError(null)
    setDraft("")
    onAsk(question)
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      {online ? null : <OfflineBanner queuedCount={0} copy={copy} />}
      <div className="phome">
        <FilingStep
          profile={profile}
          taxYear={taxYear}
          taxYearSet={taxYearSet}
          saved={saved}
          copy={copy}
          onChange={onProfile}
          onTaxYear={onTaxYear}
          onSave={() => onFilingSaved(true)}
          onEdit={() => onFilingSaved(false)}
        />
        <section className="hero" data-reveal style={{ "--i": 1 } as CSSProperties} aria-labelledby="home-title">
          <div>
            <span className="eyebrow">
              <svg className="star" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2l2.6 6.9L22 9.3l-5.6 4.7 1.8 7.2L12 17.3 5.8 21.2l1.8-7.2L2 9.3l7.4-.4z" />
              </svg>
              {tunedEyebrow(profile, taxYear, taxYearSet, copy) ?? copy("heroEyebrow")}
            </span>
            <h1 id="home-title">{copy("heroTitle")}</h1>
            <p className="sub">{copy("heroSub")}</p>
            <div className="hero-composer">
              <Composer
                value={draft}
                busy={false}
                error={error}
                preview={showPreview ? preview : null}
                copy={copy}
                placement="field"
                fieldId="home-question"
                placeholder={copy("heroPlaceholder")}
                size="large"
                showNote={false}
                onChange={(value) => {
                  setDraft(value)
                  setError(null)
                }}
                onSubmit={submit}
                onStop={() => undefined}
                muted={!online}
              />
            </div>
            <div className="chips">
              {CHIPS.map((key) => (
                <button key={key} type="button" className="hchip" onClick={() => onAsk(copy(key))}>
                  {copy(key)}
                </button>
              ))}
            </div>
          </div>
          <HeroEmblem />
        </section>
        <div className="sec-h" data-reveal style={{ "--i": 2 } as CSSProperties}>
          <h2>{copy("toolsLabel")}</h2>
          <p>{copy("toolsSub")}</p>
        </div>
        <div className="tools3">
          {TOOLS.map((tool, index) => (
            <ToolCard
              key={tool.view}
              index={3 + index}
              title={copy(`tool${tool.n}Title`)}
              description={copy(`tool${tool.n}Desc`)}
              meta={copy(`tool${tool.n}Meta`)}
              action={copy(`tool${tool.n}Go`)}
              icon={tool.icon}
              art={tool.art}
              feature={index === 0}
              badge={index === 0 ? copy("mostUsed") : undefined}
              question={copy("artQuestion")}
              estimated={copy("artEstimated")}
              onLaunch={(card) => launchFromCard(card, () => onOpen(tool.view))}
            />
          ))}
        </div>
        <div className="trust3" data-reveal style={{ "--i": 6 } as CSSProperties}>
          {TRUST.map(([title, body]) => (
            <div key={title}>
              <Icon name="checkShield" size="sm" />
              <span>
                <b>{title === "trust3Title" ? lawDateLabel(copy(title), __FBR_LAW_DATE__) : copy(title)}</b>
                {copy(body)}
              </span>
            </div>
          ))}
        </div>
        <p className="home-note">{copy("disclaimer")}</p>
      </div>
    </div>
  )
}
