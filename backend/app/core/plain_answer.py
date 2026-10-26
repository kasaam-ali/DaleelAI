"""Keep section numbers out of the main answer prose (SPEC §5.2).

Legal refs stay in sources, [n] chips, the law panel and Details. References
are removed as whole phrases ("under Section 114 of the ... Ordinance"), and
clauses that only existed to name a section are rewritten or dropped, so the
sentence still reads well. Nothing is replaced with a vague "the law".
"""

import re

_NUM = r"\d{1,3}[A-Z]{0,4}(?:\s?\(\w{1,4}\))*"
_ONE = rf"(?:Sections?|Sec\.?|s\.|§§?|u/s\.?|Rules?)\s*{_NUM}"
_REF = rf"{_ONE}(?:\s*(?:,|and|or|aur|ya|/|&)\s*(?:(?:Sections?|Sec\.?|s\.|§)\s*)?{_NUM})*"
_LAW = (
    r"(?:\s+(?:of|in)\s+the\s+(?:[A-Z][\w\-]*\s+){0,6}?(?:Ordinance|Act|Rules)"
    r"(?:,?\s*\d{4})?)?"
)
R = rf"(?:{_REF}{_LAW})"
_CHIP = r"(?:\s*(?:\[\d+\]|【\d+】))"
_I = re.I

# Run first: full-width chips and emphasis wrapped around a ref, so the ref
# phrase rules below see "is governed by Section 231AB", not "by **Section 231AB**".
_PRE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"【\s*(\d+)[^】\n]{0,40}】"), r"[\1]"),
    (re.compile(rf"(\*\*|__|\*|`)\s*({R}(?:\s*\([^()\n]{{0,60}}\))?)\s*\1"), r"\2"),
    # "Authoritative cross-reference:" is a retrieval note label, never prose.
    (re.compile(r"(?i)\**authoritative\s+cross[\s\-]?reference\**\s*:\s*"), ""),
]

_RULES: list[tuple[re.Pattern[str], str]] = [
    # A ref that is the subject of a sentence: "Section 231AB requires ..."
    (
        re.compile(
            rf"(?:\bThis\s+is\s+{R},?\s*which|\b{R}(?:\s*\([^()\n]{{0,60}}\))?)\s+"
            rf"(requires|provides|states|says|imposes|allows|covers|sets\s+out|lays\s+down)\b",
            _I,
        ),
        r"This rule \1",
    ),
    # "is covered by Section 231AB — “title”" -> "is covered by the rules on “title”"
    (
        re.compile(
            rf"\b(is|are)\s+(covered|governed|dealt\s+with)\s+(by|under|in)\s+{R}\s*[—–:-]\s*",
            _I,
        ),
        r"\1 \2 \3 the rules on ",
    ),
    # A "Reference:" / "Sources:" line or clause that only lists refs and chips.
    (
        re.compile(
            rf"(?im)^[ \t>*\-]*\**(?:references?|sources?|law|hawala|qanoon)\**\s*:\**\s*"
            rf"(?:{R}|{_CHIP}|[\s;,.]|and|aur)+$\n?"
        ),
        "",
    ),
    (
        re.compile(
            rf"\s*\**(?:references?|sources?|hawala)\**\s*:\**\s*(?:{R}|{_CHIP}|[\s;,]|and|aur)+"
            rf"(?=[.!?]?\s*$)",
            re.I | re.M,
        ),
        "",
    ),
    # Any inline "Reference:/Citations:" tail is citation-only by definition.
    (re.compile(r"(?im)[ \t]*\**(?:references?|citations?)\**[ \t]*:\**[^\n]{0,160}$"), ""),
    # Parenthetical that is only a ref, optionally with "jaise/see/e.g./i.e.".
    (
        re.compile(
            rf"\s*\(\s*(?:jaise|maslan|see|e\.g\.,?|i\.e\.,?|under|per|ref\.?)?\s*{R}\s*\)", _I
        ),
        "",
    ),
    # "X is Section 231AB" / "is covered by Section 231AB" -> "X applies".
    (
        re.compile(
            rf"\b(?:is|are)\s+(?:(?:covered|governed|dealt\s+with|set\s+out|provided|charged)\s+)?"
            rf"(?:(?:by|under|in)\s+)?{R}",
            _I,
        ),
        "applies",
    ),
    (re.compile(rf"\b(?:falls?|comes?)\s+under\s+{R}", _I), "applies"),
    # Roman Urdu: "Ordinance ke Section 118 ke tehat" keeps "Ordinance ke tehat".
    (
        re.compile(
            rf"\b(Ordinance|Act|Rules)((?:,?\s*\d{{4}})?)\s+(?:ki|ke|ka)\s+{R}\s+"
            rf"(ke\s+tehat|ke\s+tahat|ke\s+mutabiq)\b",
            _I,
        ),
        r"\1\2 \3",
    ),
    # "Section 122 notice" -> "FBR notice": keep the noun a label needs.
    (re.compile(rf"\b{R}\s+(notices?)\b", _I), r"FBR \1"),
    # Roman Urdu: "Section 149 ke tehat ...", "Section 149 lagta hai".
    (
        re.compile(
            rf"\b{R}\s+(?:ke\s+tehat|ke\s+tahat|ke\s+mutabiq|tehat|tahat|mutabiq|ke\s+under|ke\s+hisaab\s+se|mein|se)\s*",
            _I,
        ),
        "",
    ),
    (
        re.compile(rf"\b{R}\s+(?:lagta|lagti|lagte|apply\s+hota|apply\s+hoti)\b", _I),
        "yeh qanoon lagu hota",
    ),
    (re.compile(rf"\b{R}\s+(?:ka|ki|ke)\s+", _I), ""),
    # Prepositional phrases: "under Section 114 of the Ordinance", "as per s.149".
    (
        re.compile(
            rf",?\s*\b(?:under|in\s+terms\s+of|in|per|as\s+per|according\s+to|see|pursuant\s+to|"
            rf"in\s+line\s+with|vide)\s+{R}(?:\s*,)?",
            _I,
        ),
        "",
    ),
    # Anything left: drop the bare ref.
    (re.compile(rf"\b{R}", _I), ""),
]

_TIDY: list[tuple[re.Pattern[str], str]] = [
    # Truncated tails a stripped ref can leave: "is governed by." / "... dates) is."
    (
        re.compile(
            r"(?:\s+(?:is|are)\s+(?:(?:covered|governed|dealt\s+with|set\s+out|provided|charged)\s+)?"
            r"(?:by|under)|(?<=\))\s+(?:is|are))"
            r"\s*[—–-]?\s*(?=(?:\s*\[\d+\])*\s*(?:[.!?]|$))",
            re.M,
        ),
        " applies",
    ),
    (re.compile(r"\b(?:This|It)\s+applies,\s*which\s+(states|says|provides)\b"), r"This rule \1"),
    (re.compile(r"\b(covered|governed)\s+by\s*[—–:-]\s*", _I), r"\1 by the rules on "),
    # Roman Urdu postposition left without its noun: "jo ke mutabiq", "ko ke tehat", "aur tahat"
    (
        re.compile(r"\b(jo|ko|aur|ya|se|mein)\s+(?:ke\s+)?(?:tehat|tahat|mutabiq)\b\s*", _I),
        r"\1 ",
    ),
    (re.compile(r"(?m)^(\s*)(?:ke\s+)?(?:tehat|tahat|mutabiq)\b\s*", _I), r"\1"),
    # Bullet whose ref label went: "- – filing deadline" -> "- filing deadline"
    (re.compile(r"(?m)^([ \t]*[-*])[ \t]*[—–:-][ \t]*"), r"\1 "),
    # Bullet that lost its subject ref: "- Requires every bank ..."
    (
        re.compile(r"(?m)^([ \t]*[-*][ \t]+)(Requires|Provides|Imposes|States|Allows|Says)\b"),
        lambda m: m.group(1) + "This rule " + m.group(2).lower(),
    ),
    # A line that is only chips: "[1]."
    (re.compile(r"(?m)^[ \t]*(?:\[\d+\][ \t]*)+[.,;]?[ \t]*$\n?"), ""),
    (re.compile(r"\(\s*(?:jaise|maslan|see|e\.g\.,?|i\.e\.,?)?\s*[,;/]*\s*\)", _I), ""),
    (re.compile(r"\[\s*\]"), ""),
    (re.compile(r"\*\*\s*\*\*"), ""),
    (re.compile(r"\b(?:under|per|as per|according to)\s*(?=[,.;:!?]|$)", _I | re.M), ""),
    (re.compile(r"(?m)^([ \t]*[-*>]?[ \t]*),\s*"), r"\1"),
    (re.compile(r"[^\S\n]+([.,;:!?)\]】])"), r"\1"),
    (re.compile(r"([,;])\s*(?=[,;.])"), ""),
    (re.compile(r"\(\s+"), "("),
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r"(?m)^[ \t]*[-*][ \t]*[.,;:]?[ \t]*$\n?"), ""),
]

_CAP = re.compile(r"(^\s*(?:[-*>][ \t]+)?|[.!?]\s+|\n[ \t]*(?:[-*>][ \t]+)?)([a-z])")


_REF_HEAD = re.compile(
    r"^[ \t>#]*[*_]*\s*(?:references?|citations?|sources?|hawala(?:jat)?)\s*[*_]*\s*:?\s*[*_]*\s*$",
    re.I,
)
_BULLET = re.compile(r"^[ \t]*(?:[-*•]|\d+[.)])[ \t]")


def _drop_ref_blocks(text: str, in_block: bool = False) -> tuple[str, bool]:
    """Drop a "References"/"Citations" heading and the bullet list under it.

    The sources strip already lists them with their sections. Returns the
    text and whether we are still inside such a block (for streaming).
    """
    kept: list[str] = []
    for line in text.split("\n"):
        if _REF_HEAD.match(line):
            in_block = True
            continue
        if in_block:
            if _BULLET.match(line):
                continue
            if not line.strip():
                continue
            in_block = False
        kept.append(line)
    return "\n".join(kept), in_block


def _cap_chips(text: str, n_sources: int | None) -> str:
    if not n_sources:
        return text
    return re.sub(r"\[(\d+)\]", lambda m: m.group(0) if int(m.group(1)) <= n_sources else "", text)


def plain_answer(text: str, language: str = "en", n_sources: int | None = None) -> str:
    out, _ = _drop_ref_blocks(_pre(text or ""))
    out = _drop_broken(_strip(out, n_sources))
    return out.strip()


# Structural signs that a sentence lost a noun when a ref was stripped. These
# are generic shapes (a preposition or postposition with nothing after it, a
# lone "applies", unmatched brackets), not one rule per answer we have seen.
_END = r"(?=(?:\[\d+\])*\s*[.!?;:]?\s*$)"
_STRANDED = re.compile(
    r"\b(?:of|by|under|per)\s+(?:apply|applies|is|are)\b"
    rf"|\b(?:of|by|under|to|per|and|or|the|with|see){_END}"
    rf"|\b(?:and|or)\s+the\s+[A-Z]\w*\s+Schedule{_END}"
    r"|\b(?:specified|prescribed|provided|mentioned)\s+and\s+the\b"
    r"|\b(?:ko|jo|se|ka|aur|ya)\s+(?:tehet|tehat|tahat|mutabiq)\b"
    rf"|\b(?:tehet|tehat|tahat|mutabiq|ke|ki|ka|ko|mein){_END}"
    r"|\bjo\s+ya\s+to\b"
    r"|\bcross[\s\-\u2010\u2011]?references?\b"
    r"|\bin\s+the\s+(?:provided\s+)?context\b"
    r"|^\W*\)?\s*applies\b"
    # A legal noun with no content left: "The only provision (...) applies."
    rf"|^\W*(?:the\s+)?(?:only\s+|relevant\s+|special\s+)*(?:provisions?|rules?|clauses?)\b"
    rf"[^.!?]*\bappl(?:y|ies){_END}",
    re.I,
)
# Sentence end: punctuation (plus chips) then space and a capital, bracket or bullet.
_SPLIT = re.compile(
    r"(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\bRs\.)(?<!\bNo\.)(?<=[.!?])"
    r"((?:\s*\[\d+\])*)[ \t]+(?=[A-Z(\[*\-])"
)


def _broken(sentence: str) -> bool:
    body = re.sub(r"\[\d+\]", "", sentence).strip(" \t-*>#")
    if not body:
        return False
    if body.count("(") != body.count(")"):
        return True
    if body.startswith("(") and body.rstrip(".!? ").endswith(")"):
        return True  # only a parenthetical fragment
    words = len(re.findall(r"[A-Za-z]{2,}", body))
    if words < 2 and not re.search(r"\d", body) and not body.endswith(":"):
        return True  # debris such as "applies." or a lone "("
    return bool(_STRANDED.search(body))


def _drop_broken_line(line: str) -> str:
    lead = re.match(r"^[ \t]*(?:[-*•>]|\d+[.)])?[ \t]*", line).group(0)
    rest = _SPLIT.sub(lambda m: m.group(1) + "\x00", line[len(lead) :])
    parts = rest.split("\x00")
    kept = [part.strip() for part in parts if not _broken(part)]
    if len(kept) == len(parts):
        return line
    body = " ".join(p for p in kept if p)
    if not body and line.strip():
        return "\x01"  # whole line was broken: drop it
    return lead + body


def _drop_broken(text: str) -> str:
    """Drop sentences left grammatically broken after the ref strip."""
    lines = [_drop_broken_line(line) for line in text.split("\n")]
    out = "\n".join(line for line in lines if line != "\x01")
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return re.sub(r"\n{3,}", "\n\n", out)


def _pre(text: str) -> str:
    for pattern, repl in _PRE:
        text = pattern.sub(repl, text)
    return text


def _strip(out: str, n_sources: int | None = None) -> str:
    out = _cap_chips(out, n_sources)
    for pattern, repl in _RULES:
        out = pattern.sub(repl, out)
    for pattern, repl in _TIDY:
        out = pattern.sub(repl, out)
    out = _CAP.sub(lambda m: m.group(1) + m.group(2).upper(), out)
    return out


_ANY_REF = re.compile(rf"\b{_ONE}", _I)
# A stream piece may end mid-reference ("... under Sec", "Section 11", "of the Income").
_SAFE_END = re.compile(r"(?<!\bs)(?<!\bSec)(?<!\bu/s)(?<!\bNo)[.!?](?:\s+)|\n")


# Word starts that may grow into a ref or a "Reference:" line, or an open "(".
_MAYBE_REF = re.compile(r"\b(?:s\b|s\.|se|u/|ref|sou|haw|law|qan)|§|\(", re.I)
_KEEP_WORDS = 4


class PlainStream:
    """Clean streamed tokens without ever emitting a partial reference.

    Text is held until a sentence or line ends, so a ref split across chunks
    ("Sec" + "tion 1" + "14") is cleaned as a whole. Each released piece is
    cleaned with the same rules as the final answer.
    """

    def __init__(self, language: str = "en", max_hold: int = 600) -> None:
        self.language = language
        self.max_hold = max_hold
        self._buf = ""
        self._started = False
        self._in_refs = False
        # True when the next piece starts a fresh sentence, so whole-sentence
        # checks are safe. Word-level releases mid-sentence skip them.
        self._at_start = True

    def push(self, text: str) -> str:
        self._buf += text or ""
        cut = 0
        for m in _SAFE_END.finditer(self._buf):
            cut = m.end()
        rest = self._buf[cut:]
        if not _MAYBE_REF.search(rest):
            # No ref can be forming: release words, keeping the last few back
            # so "is covered by" / "according to" can still meet a ref.
            spaces = [m.start() for m in re.finditer(r"\s+", rest)]
            if len(spaces) > _KEEP_WORDS:
                cut += spaces[-_KEEP_WORDS - 1] + 1
        elif len(self._buf) - cut > self.max_hold:
            cut = max(cut, self._buf.rfind(" ", 0, len(self._buf) - 120) + 1)
        if cut <= 0:
            return ""
        ready, self._buf = self._buf[:cut], self._buf[cut:]
        return self._clean(ready)

    def flush(self) -> str:
        ready, self._buf = self._buf, ""
        return self._clean(ready, final=True) if ready else ""

    def _clean(self, piece: str, final: bool = False) -> str:
        lead = piece[: len(piece) - len(piece.lstrip())]
        tail = piece[len(piece.rstrip()) :]
        text, self._in_refs = _drop_ref_blocks(_pre(piece), self._in_refs)
        body = _strip(text)
        whole = self._at_start and (final or bool(re.search(r"[.!?\n]\s*$", piece)))
        self._at_start = bool(re.search(r"[.!?\n]\s*$", piece))
        if whole:
            body = _drop_broken(body)
        body = body.strip()
        if not body:
            return "\n" if "\n" in piece else ""
        if not self._started:
            lead = ""
        first = piece.lstrip()[:1]
        if first.islower() and body[:1] == first.upper():
            body = first + body[1:]  # forced cut mid-sentence: keep the case
        self._started = True
        return lead + body + tail
