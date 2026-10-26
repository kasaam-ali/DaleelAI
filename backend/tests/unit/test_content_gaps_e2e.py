from app.agents.router import lexicon_route
from app.core.plain_answer import plain_answer
from app.core.retrieval.rewrite import detect_topics
from app.core.tax_engine import _amount


def test_section_number_is_not_income():
    q = "How is salary tax calculated under section 149 for TY2027?"
    assert _amount(q, {}) is None
    assert lexicon_route(q).intent == "qa"


def test_real_amount_still_calculates():
    assert lexicon_route("salary tax on 1,200,000").intent == "calculate"


def test_pension_question_gets_pension_topic():
    keys = {t.key for t in detect_topics("pension wale buzurg ko bhi tax dena parta hai kya?")}
    assert "pension" in keys


def test_ru_ordinance_keeps_postposition():
    out = plain_answer(
        "Yeh due date Income Tax Ordinance ke Section 118 ke tehat hoti hai.", "roman_urdu"
    )
    assert out == "Yeh due date Income Tax Ordinance ke tehat hoti hai."


def test_notice_label_keeps_noun():
    out = plain_answer(
        "- **Section 122 notice**: FBR assessment amend kar sakta hai.", "roman_urdu"
    )
    assert "**FBR notice**:" in out


def test_rule_number_does_not_leak():
    out = plain_answer("Rule 231FA ke mutabiq bank tax kaat-ta hai.", "roman_urdu")
    assert "231FA" not in out and "Rule" not in out


from app.agents.answer import _generate_messages  # noqa: E402
from app.core.retrieval.expand import ContextBlock  # noqa: E402


def _system(blocks):
    msgs = _generate_messages(
        question="q",
        language="english",
        tax_year="2026",
        corpus_date="2026-07-01",
        blocks=blocks,
        mode="library",
    )
    return msgs[0].content


def test_no_filing_dates_without_114_118():
    s = _system([ContextBlock(parent_id="s149", text="Section 149 Salary. Tax on salary.")])
    assert "30 September" not in s and "31 December" not in s
    assert "Do not state any return filing due date" in s
    assert "taxpayer kind" not in s


def test_filing_dates_rule_with_118():
    s = _system([ContextBlock(parent_id="s118", text="Section 118 Method of furnishing returns.")])
    assert "exactly as the context states" in s
    assert "never give companies the individuals' date" in s


def test_sub_section_debris_removed():
    out = plain_answer("FBR show-cause notice (sub-) bhejta hai.", "roman_urdu")
    assert "(sub" not in out
