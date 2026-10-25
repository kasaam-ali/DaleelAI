"""SPEC §5.2: refs leave the prose as whole phrases, with no junk left behind."""

import re

import pytest

from app.core.plain_answer import PlainStream, plain_answer

REF = re.compile(
    r"§|\bs\.\s?\d|\bsec(?:tion)?s?\b\.?\s*\d|\bthe law\b|\(\s*\)|\(jaise\s*\)|\[\s*\]", re.I
)

CASES = [
    (
        "en",
        "Under Section 114 of the Income Tax Ordinance, 2001, you must file by 30 September [1].",
        "You must file by 30 September [1].",
    ),
    (
        "en",
        "Advance tax on cash withdrawal is Section 231AB [1].",
        "Advance tax on cash withdrawal applies [1].",
    ),
    (
        "en",
        "Seller advance tax is Section 236C and buyer advance tax is Section 236K [2].",
        "Seller advance tax applies and buyer advance tax applies [2].",
    ),
    (
        "en",
        "You must file on time [1].\n\n**Reference:** Section 114 [1]; Section 118 [2].",
        "You must file on time [1].",
    ),
    ("en", "Reference: Section 114; Section 118", ""),
    (
        "en",
        "Late filing (Section 182) can bring a penalty [1].",
        "Late filing can bring a penalty [1].",
    ),
    (
        "en",
        "Your employer deducts tax as per s.149 [1]. "
        "Rates are in the First Schedule (s. 149(1)) [1].",
        "Your employer deducts tax [1]. Rates are in the First Schedule [1].",
    ),
    (
        "roman_urdu",
        "Salary par tax (jaise Section 149) apply hota hai [1].",
        "Salary par tax apply hota hai [1].",
    ),
    (
        "roman_urdu",
        "Section 149 ke tehat aap ka employer har mahine tax kaat-ta hai [1].",
        "Aap ka employer har mahine tax kaat-ta hai [1].",
    ),
]


@pytest.mark.parametrize(("lang", "raw", "want"), CASES)
def test_phrase_aware_rewrite(lang, raw, want):
    got = plain_answer(raw, lang)
    assert got == want
    assert not REF.search(got)


def test_plain_text_untouched():
    text = "File by 30 September [1].\n\n- Keep receipts.\n- Pay on time [2]."
    assert plain_answer(text) == text


def _stream(chunks, lang="en"):
    s = PlainStream(lang)
    out = [s.push(c) for c in chunks]
    out.append(s.flush())
    return out


PARTIAL = re.compile(r"\b(?:Se|Sec|Sect|Secti|Sectio|Section|s\.|§)\s*\d*\s*$", re.I)


@pytest.mark.parametrize(
    ("lang", "chunks"),
    [
        (
            "en",
            [
                "You must file by 30 Sep under Sec",
                "tion",
                " 11",
                "4 of the Income Tax Ord",
                "inance, 2001 [1]. Late ",
                "filing (Section 182) brings a penalty.",
            ],
        ),
        ("en", ["Under Section", " 114, you must file", " by 30 September [1].\n", "Pay on time."]),
        (
            "roman_urdu",
            ["Salary par tax (jaise Sec", "tion 149) apply hota hai [1]. ", "Shukriya."],
        ),
    ],
)
def test_stream_never_shows_ref_mid_stream(lang, chunks):
    shown = ""
    s = PlainStream(lang)
    for chunk in chunks:
        shown += s.push(chunk)
        assert not REF.search(shown), shown
        assert not PARTIAL.search(shown), shown
    shown += s.flush()
    assert not REF.search(shown)
    assert " ".join(shown.split()) == " ".join(plain_answer("".join(chunks), lang).split())


def test_stream_long_run_without_full_stop_still_flows():
    s = PlainStream("en", max_hold=200)
    released = s.push("word " * 100)
    assert released.startswith("word word")
    rest = s.flush()
    assert " ".join((released + rest).split()) == " ".join(["word"] * 100)


def test_char_by_char_stream_never_flashes_a_ref():
    text = (
        "Under Section 114 of the Income Tax Ordinance, 2001, you must file by 30 September [1]. "
        "Advance tax on cash withdrawal is Section 231AB [2].\n\n**Reference:** Section 114 [1]; "
        "Section 231AB [2]."
    )
    s = PlainStream("en")
    shown = ""
    for ch in text:
        shown += s.push(ch)
        assert not REF.search(shown), shown
        assert not PARTIAL.search(shown), shown
    shown += s.flush()
    assert " ".join(shown.split()) == " ".join(plain_answer(text).split())
