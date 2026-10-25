"""Keep section numbers out of the main answer prose (SPEC §5.2).

Legal refs stay in sources, [n] chips, the law panel and Details. References
are removed as whole phrases ("under Section 114 of the ... Ordinance"), and
clauses that only existed to name a section are rewritten or dropped, so the
sentence still reads well. Nothing is replaced with a vague "the law".
"""

import re

_NUM = r"\d{1,3}[A-Z]{0,4}(?:\s?\(\w{1,4}\))*"
_ONE = rf"(?:Sections?|Sec\.?|s\.|§§?|u/s\.?)\s*{_NUM}"
_REF = rf"{_ONE}(?:\s*(?:,|and|or|aur|ya|/|&)\s*(?:(?:Sections?|Sec\.?|s\.|§)\s*)?{_NUM})*"
_LAW = (
    r"(?:\s+(?:of|in)\s+the\s+(?:[A-Z][\w\-]*\s+){0,6}?(?:Ordinance|Act|Rules)"
    r"(?:,?\s*\d{4})?)?"
)
R = rf"(?:{_REF}{_LAW})"
_CHIP = r"(?:\s*(?:\[\d+\]|【\d+】))"
_I = re.I

_RULES: list[tuple[re.Pattern[str], str]] = [
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
    # Roman Urdu: "Section 149 ke tehat ...", "Section 149 lagta hai".
    (
        re.compile(
            rf"\b{R}\s+(?:ke\s+tehat|ke\s+mutabiq|ke\s+under|ke\s+hisaab\s+se|mein|se)\s*", _I
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
    (re.compile(r"\(\s*(?:jaise|maslan|see|e\.g\.,?|i\.e\.,?)?\s*[,;/]*\s*\)", _I), ""),
    (re.compile(r"\[\s*\]"), ""),
    (re.compile(r"\*\*\s*\*\*"), ""),
    (re.compile(r"\b(?:under|per|as per|according to)\s*(?=[,.;:!?]|$)", _I | re.M), ""),
    (re.compile(r"(?m)^([ \t]*[-*>]?[ \t]*),\s*"), r"\1"),
    (re.compile(r"[ \t]+([.,;:!?)\]】])"), r"\1"),
    (re.compile(r"([,;])\s*(?=[,;.])"), ""),
    (re.compile(r"\(\s+"), "("),
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r"(?m)^[ \t]*[-*][ \t]*[.,;:]?[ \t]*$\n?"), ""),
]

_CAP = re.compile(r"(^\s*|[.!?]\s+|\n[ \t]*(?:[-*>][ \t]+)?)([a-z])")


def plain_answer(text: str, language: str = "en") -> str:
    out = text or ""
    for pattern, repl in _RULES:
        out = pattern.sub(repl, out)
    for pattern, repl in _TIDY:
        out = pattern.sub(repl, out)
    out = _CAP.sub(lambda m: m.group(1) + m.group(2).upper(), out)
    return out.strip()


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
        return self._clean(ready) if ready else ""

    def _clean(self, piece: str) -> str:
        lead = piece[: len(piece) - len(piece.lstrip())]
        tail = piece[len(piece.rstrip()) :]
        body = plain_answer(piece, self.language)
        if not body:
            return "\n" if "\n" in piece else ""
        if not self._started:
            lead = ""
        first = piece.lstrip()[:1]
        if first.islower() and body[:1] == first.upper():
            body = first + body[1:]  # forced cut mid-sentence: keep the case
        self._started = True
        return lead + body + tail
