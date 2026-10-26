/** The answer as sanitized Markdown, with [n] markers turned into citation chips. */

import { createContext, useContext, type ReactNode } from "react"
import Markdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import type { Source } from "../../../api/chat"
import { safeHref } from "../../../lib/safeUrl"
import CitationChip from "./CitationChip"
import { linkCitations } from "./refs"
import type { Copy, OpenSource } from "./types"

const REF_HEADER = /^(ref|reference|hawala|section|dafa|source)/i

type CiteContext = {
  sources: Source[]
  turnId: string
  activeCite: number | null
  copy: Copy
  onOpen: OpenSource
}

const Cites = createContext<CiteContext | null>(null)

function Link({ href, children }: { href?: string; children?: ReactNode }) {
  const cites = useContext(Cites)
  const cite = /^#cite-(\d+)$/.exec(href ?? "")
  if (cite) {
    const n = Number(cite[1])
    const source = cites?.sources[n - 1]
    if (!cites || !source) return <>{children}</>
    return (
      <CitationChip
        n={n}
        source={source}
        turnId={cites.turnId}
        active={cites.activeCite === n}
        copy={cites.copy}
        onOpen={cites.onOpen}
      />
    )
  }
  const safe = safeHref(href)
  if (!safe) return <>{children}</>
  return (
    <a href={safe} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  )
}

/** Stable across renders so chips keep their DOM node (focus returns to them when the panel closes). */
const COMPONENTS: Components = {
  a: ({ href, children }) => <Link href={href}>{children}</Link>,
  h1: ({ children }) => <h3>{children}</h3>,
  h2: ({ children }) => <h3>{children}</h3>,
  h4: ({ children }) => <h3>{children}</h3>,
  img: () => null,
  table: ({ children }) => (
    <div className="tw">
      <table>{children}</table>
    </div>
  ),
}

export default function AnswerBody({
  text,
  sources,
  turnId,
  activeCite,
  streaming,
  lang,
  copy,
  onOpen,
}: {
  text: string
  sources: Source[]
  turnId: string
  activeCite: number | null
  streaming: boolean
  lang: string
  copy: Copy
  onOpen: OpenSource
}) {
  return (
    <Cites.Provider value={{ sources, turnId, activeCite, copy, onOpen }}>
      <div className="answer" lang={lang} data-answer-body>
        <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRefColumn]} components={COMPONENTS} skipHtml>
          {linkCitations(text, sources.length)}
        </Markdown>
        {streaming ? <span className="caret" aria-hidden="true" /> : null}
      </div>
    </Cites.Provider>
  )
}

/** Tables whose last header is a reference column (Ref / Hawala / Section) get .ref cells, as in the mockup. */
type HastNode = { type: string; tagName?: string; value?: string; properties?: Record<string, unknown>; children?: HastNode[] }

function rehypeRefColumn() {
  return (tree: HastNode) => {
    walk(tree, (node) => {
      if (node.tagName !== "table") return
      const rows = collect(node, "tr")
      const head = rows[0] ? cellsOf(rows[0]) : []
      if (!head.length || !REF_HEADER.test(textOf(head[head.length - 1]).trim())) return
      for (const row of rows.slice(1)) {
        const cells = cellsOf(row)
        const last = cells[cells.length - 1]
        if (last && last.tagName === "td") last.properties = { ...last.properties, className: ["ref"] }
      }
    })
  }
}

function walk(node: HastNode, visit: (node: HastNode) => void) {
  visit(node)
  for (const child of node.children ?? []) walk(child, visit)
}

function collect(node: HastNode, tag: string): HastNode[] {
  const found: HastNode[] = []
  walk(node, (child) => {
    if (child.tagName === tag) found.push(child)
  })
  return found
}

function cellsOf(row: HastNode): HastNode[] {
  return (row.children ?? []).filter((child) => child.tagName === "td" || child.tagName === "th")
}

function textOf(node: HastNode): string {
  if (node.type === "text") return node.value ?? ""
  return (node.children ?? []).map(textOf).join("")
}
