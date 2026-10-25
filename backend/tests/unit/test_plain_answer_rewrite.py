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


# QA retest @ 2293db6: raw model text that left orphan fragments after the strip.
ORPHANS = [
    # 1) truncated tails
    (
        "en",
        "The advance tax on cash withdrawal for persons who are **not on the Active Taxpayers "
        "List (non-filers)** is governed by **Section 231AB**.",
        "The advance tax on cash withdrawal for persons who are **not on the Active Taxpayers "
        "List (non-filers)** applies.",
    ),
    (
        "en",
        "The advance tax on cash withdrawal is covered by **Section 231AB** — "
        "“Advance tax on cash withdrawal” [1][2].",
        "The advance tax on cash withdrawal is covered by the rules on "
        "“Advance tax on cash withdrawal” [1][2].",
    ),
    (
        "en",
        "Advance tax for non-filers (people who have not filed a return by the due dates) is "
        "Section 236K [1].",
        "Advance tax for non-filers (people who have not filed a return by the due dates) "
        "applies [1].",
    ),
    (
        "en",
        "This is Section 231AB, which states that banks deduct 0.8% [1].",
        "This rule states that banks deduct 0.8% [1].",
    ),
    (
        "en",
        "- **Section 231AB(1)** requires every banking company to deduct tax [1].",
        "- This rule requires every banking company to deduct tax [1].",
    ),
    # orphans already stripped by an older build must also be repaired
    (
        "en",
        "Cash withdrawal tax (non-filers) is governed by.",
        "Cash withdrawal tax (non-filers) applies.",
    ),
    (
        "en",
        "Rates are listed in the First Schedule [1].",
        "Rates are listed in the First Schedule [1].",
    ),
    # 2) empty Reference / Citations lines and label-less bullets
    (
        "en",
        "File by 31 December [1].\n\n**References**\n- **Section 118** – filing deadline for "
        "companies [1]\n- **Section 114** – who must file a return [2]",
        "File by 31 December [1].",
    ),
    (
        "roman_urdu",
        "Return due date se pehle file karein [1].\n\n**Citations:**\n- **Section 118** – due "
        "date for furnishing return [1]\n- – notice ke zariye due date [1]",
        "Return due date se pehle file karein [1].",
    ),
    ("en", "Pay on time [1]. Reference: and the Tenth Schedule 1.", "Pay on time [1]."),
    ("en", "- – filing deadline for companies [1]", "- Filing deadline for companies [1]"),
    ("en", "Keep receipts [1].\n\n[1].", "Keep receipts [1]."),
    # 3) Roman Urdu hanging postpositions
    (
        "roman_urdu",
        "Aakhri tareekh woh din hai jo **Section 118** ke mutabiq “due date” hai [1].",
        "Aakhri tareekh woh din hai jo “due date” hai [1].",
    ),
    (
        "roman_urdu",
        "Agar taxpayer ko Section 114(4) ke tehat notice milti hai [1].",
        "Agar taxpayer ko notice milti hai [1].",
    ),
    (
        "roman_urdu",
        "Withheld tax aur Section 149(3) tahat admissible tax credit ka adjustment [1].",
        "Withheld tax aur admissible tax credit ka adjustment [1].",
    ),
    (
        "roman_urdu",
        "Agar taxpayer ko ke tehat notice milti hai.",
        "Agar taxpayer ko notice milti hai.",
    ),
    ("roman_urdu", "Woh din hai jo ke mutabiq due date hai.", "Woh din hai jo due date hai."),
    ("roman_urdu", "Tax aur tahat admissible credit.", "Tax aur admissible credit."),
    (
        "roman_urdu",
        "Employee ke “Salary” head ke tehat tax.",
        "Employee ke “Salary” head ke tehat tax.",
    ),
    # 4) full-width citation markup
    ("en", "File by 30 September【1†L10-L12】.", "File by 30 September[1]."),
    (
        "roman_urdu",
        "Bank tax kaatta hai 【1】 aur rate 0.8% hai 【2】.",
        "Bank tax kaatta hai [1] aur rate 0.8% hai [2].",
    ),
    # 5) retrieval-note label leaking into prose
    (
        "en",
        "Authoritative cross-reference: Advance tax on cash withdrawal is Section 231AB. "
        "Banks deduct 0.8% [1].",
        "Advance tax on cash withdrawal applies. Banks deduct 0.8% [1].",
    ),
]


@pytest.mark.parametrize(("lang", "raw", "want"), ORPHANS)
def test_no_orphans_after_strip(lang, raw, want):
    got = plain_answer(raw, lang)
    assert got == want
    assert not REF.search(got)
    assert not re.search(r"【|\b(?:by|is)\s*[—–]?\s*[.]|^\s*[-*]\s*[–—]|cross-reference", got, re.M)


def test_chips_never_point_past_sources():
    got = plain_answer("Banks deduct tax [3]. Filers are exempt [1][2].", n_sources=2)
    assert got == "Banks deduct tax. Filers are exempt [1][2]."


def test_stream_drops_reference_block_across_chunks():
    chunks = [
        "File by 31 December [1].\n\n",
        "**References**\n",
        "- **Section 118** – filing deadline [1]\n",
        "- **Section 114** – who must file [2]",
    ]
    s = PlainStream("en")
    shown = "".join(s.push(c) for c in chunks) + s.flush()
    assert shown.strip() == "File by 31 December [1]."


def test_already_stripped_bullet_gets_a_subject_and_no_space_before_dot():
    raw = "- Requires every bank to **deduct 0.8%**\u202f[3]. \n- Filers are exempt [1]."
    got = plain_answer(raw, n_sources=2)
    assert got == "- This rule requires every bank to **deduct 0.8%**. \n- Filers are exempt [1]."


@pytest.mark.parametrize(
    ("draft", "want"),
    [
        (
            "Special provisions of Section 100BA apply. Under this rule, non-filers pay more [1].",
            "Under this rule, non-filers pay more [1].",
        ),
        (
            "Tax is charged at the higher tax rate specified in Section 100BA and the Tenth "
            "Schedule. Filers pay less [2].",
            "Filers pay less [2].",
        ),
        (
            "The only provision (for persons who have not filed a return by the due dates) "
            "is Section 100BA. Keep records [1].",
            "Keep records [1].",
        ),
        (
            "Banks deduct tax [1]. (applies to persons not on the Active Taxpayers List; filers "
            "are exempt – see the cross-reference in the context[1].)",
            "Banks deduct tax [1].",
        ),
        (
            "Agar taxpayer ko Section 114 ke tehet notice jari hota hai. "
            "Return 30 September tak file karein [1].",
            "Return 30 September tak file karein [1].",
        ),
        ("Return jo ya to likha ho. Return file karein [1].", "Return file karein [1]."),
        ("Last date 30 September hai [1]. (", "Last date 30 September hai [1]."),
        (
            "The authoritative cross-reference states that this tax applies [1]. "
            "Pay by 30 June [2].",
            "Pay by 30 June [2].",
        ),
    ],
)
def test_broken_sentences_are_dropped(draft, want):
    assert plain_answer(draft) == want


def test_good_sentences_and_abbreviations_survive_the_drop():
    draft = "Rs. 50,000 is taxed at 5% [1]. Employee ke “Salary” head ke tehat tax [2]."
    assert plain_answer(draft) == draft


def test_stream_drops_broken_sentences_like_final():
    draft = "Special provisions of Section 100BA apply. Pay tax by 30 June [1]. ("
    stream = PlainStream()
    pieces = ["Special provisions of Sec", "tion 100BA apply. ", "Pay tax by 30 June [1]. ("]
    out = "".join(stream.push(p) for p in pieces) + stream.flush()
    assert out.strip() == plain_answer(draft) == "Pay tax by 30 June [1]."
