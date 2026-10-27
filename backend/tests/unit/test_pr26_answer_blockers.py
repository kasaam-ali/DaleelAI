from app.agents.answer import _generate_messages, block_text
from app.core.plain_answer import EMPTY_FALLBACK, plain_answer
from app.core.retrieval.expand import ContextBlock

DEC = ContextBlock(
    parent_id="s118",
    text="Section 118 ... thirty-first day of December next following the end of the tax year; "
    "(b) in any other case, the thirtieth day of September.",
)


def test_empty_after_strip_falls_back_roman_urdu():
    out = plain_answer("Due date context mein mention nahi hai.", "roman_urdu", fallback=True)
    assert out == EMPTY_FALLBACK["roman_urdu"]


def test_empty_after_strip_falls_back_en():
    out = plain_answer("The provided information does not specify the date.", "en", fallback=True)
    assert out == EMPTY_FALLBACK["en"]


def test_meta_paraphrases_stripped_keeps_rest():
    text = (
        "Individuals file by 30 September 2026 [1]. "
        "The provided rules do not give a company date. "
        "No specific date is in the available information."
    )
    out = plain_answer(text, "en")
    assert "30 September 2026" in out
    assert "provided" not in out and "available information" not in out


def test_company_date_chunk_gets_company_lead_in():
    assert "in the case of a company" in block_text(DEC)
    msgs = _generate_messages(
        question="company filing date?",
        language="en",
        tax_year="2026",
        corpus_date="2026-07-01",
        blocks=[DEC],
        mode="library",
    )
    assert (
        "in the case of a company, on or before the thirty-first day of December" in msgs[1].content
    )
    assert "31 December" in msgs[0].content


def test_other_chunks_unchanged():
    b = ContextBlock(parent_id="s149", text="Section 149 taxes salary.")
    assert block_text(b) == b.text
