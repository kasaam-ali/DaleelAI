import { useEffect, useState } from "react"
import { ablationReport, classifierReport, type AblationReport, type ClassifierReport } from "../../api/experts"
import type { CopyKey } from "../../i18n"

type Copy = (key: CopyKey) => string

export default function EvaluationPage({ copy }: { copy: Copy }) {
  const [report, setReport] = useState<ClassifierReport | null>(null)
  const [ablation, setAblation] = useState<AblationReport | null>(null)
  const [missing, setMissing] = useState(false)
  const [ablationMissing, setAblationMissing] = useState(false)

  useEffect(() => {
    let active = true
    classifierReport()
      .then((next) => {
        if (active) setReport(next)
      })
      .catch(() => {
        if (active) setMissing(true)
      })
    ablationReport()
      .then((next) => {
        if (active) setAblation(next)
      })
      .catch(() => {
        if (active) setAblationMissing(true)
      })
    return () => {
      active = false
    }
  }, [])

  const served = report?.candidates.find((item) => item.name === report.served_model)
  return (
    <section className="mt-8">
      <h2 className="font-statute text-3xl">{copy("evalTitle")}</h2>
      {missing ? <p className="mt-3 text-sm text-muted">{copy("evalMissing")}</p> : null}
      {report ? (
        <div className="mt-4 grid gap-4">
          <p className="text-sm text-muted">{report.served_model}</p>
          {report.candidates.map((item) => (
            <article key={item.name} className="border border-rule bg-field px-4 py-4 text-sm">
              <h3 className="font-medium">{item.name}</h3>
              <ScoreTable copy={copy} label={copy("evalHuman")} score={item.human_test} />
              <ScoreTable copy={copy} label={copy("evalSynthetic")} score={item.synthetic_test} />
            </article>
          ))}
          {served ? <Matrix score={served.human_test} /> : null}
          <ul className="grid gap-2 text-sm text-muted">
            {report.not_trained.map((item) => (
              <li key={item.name}>
                {item.name}: {item.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <h3 className="mt-8 font-statute text-2xl">{copy("evalAblationTitle")}</h3>
      {ablationMissing ? <p className="mt-3 text-sm text-muted">{copy("evalAblationMissing")}</p> : null}
      {ablation ? <AblationTable copy={copy} report={ablation} /> : null}
    </section>
  )
}

function AblationTable({ copy, report }: { copy: Copy; report: AblationReport }) {
  return (
    <div className="mt-4 grid gap-3">
      <p className="text-sm text-muted">
        {report.dataset.total} questions. English {report.dataset.en}, Roman Urdu {report.dataset.roman_urdu}.
        Special cases {report.dataset.special} are included in those counts. Dev {report.dataset.dev}, test{" "}
        {report.dataset.test}. Sample {report.sample_size}.
      </p>
      <div className="overflow-x-auto border border-rule">
        <table className="w-full text-left text-sm">
          <thead>
            <tr>
              <th className="px-3 py-2">Stage</th>
              <th className="px-3 py-2">{copy("evalRecall")}</th>
              <th className="px-3 py-2">{copy("evalLatency")}</th>
            </tr>
          </thead>
          <tbody>
            {report.stages.map((stage) => {
              const score = stage.recall_at_5 ?? stage.coverage
              return (
                <tr key={stage.name} className="border-t border-rule">
                  <td className="px-3 py-2">
                    <p>{stage.name}</p>
                    <p className="max-w-[42ch] text-xs text-muted">{stage.reason}</p>
                  </td>
                  <td className="px-3 py-2">
                    {score == null ? (
                      stage.status
                    ) : (
                      <div>
                        <p>
                          {stage.recall_at_5 == null ? copy("evalCoverage") : copy("evalRecall")} {score}
                        </p>
                        <div className="mt-1 h-3 w-32 border border-rule bg-paper">
                          <div className="h-full bg-seal" style={{ width: `${Math.round(score * 100)}%` }} />
                        </div>
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2">{stage.mean_latency_ms == null ? "" : `${stage.mean_latency_ms} ms`}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ScoreTable({
  copy,
  label,
  score,
}: {
  copy: Copy
  label: string
  score: ClassifierReport["candidates"][number]["human_test"]
}) {
  return (
    <p className="mt-2">
      {label}: macro-F1 {score.macro_f1}, accuracy {score.accuracy}, en {score.per_language_f1.en},
      Roman Urdu {score.per_language_f1.roman_urdu}. {copy("evalLatency")} {score.latency_ms_mean} ms
    </p>
  )
}

function Matrix({ score }: { score: ClassifierReport["candidates"][number]["human_test"] }) {
  const { labels, matrix } = score.confusion_matrix
  return (
    <div className="overflow-x-auto border border-rule">
      <table className="w-full text-left text-xs">
        <thead>
          <tr>
            <th className="px-2 py-2"> </th>
            {labels.map((label) => (
              <th key={label} className="px-2 py-2 font-medium">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, index) => (
            <tr key={labels[index]}>
              <th className="px-2 py-1 font-medium">{labels[index]}</th>
              {row.map((value, column) => (
                <td key={`${labels[index]}-${labels[column]}`} className="px-2 py-1">
                  {value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
