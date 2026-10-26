from app.core.deadline_binder import bind_filing_dates
from app.core.plain_answer import plain_answer

DEC = "118(2) (a) in the case of a company, on or before the thirty-first day of December next following the end of the tax year"
SEP = "118 (b) in the case of a person other than a company, the thirtieth day of September next following the end of the tax year"


def test_company_ask_gets_dec31():
    out = bind_filing_dates(
        "The return must be filed with FBR.", "company return filing deadline?", [DEC], "TY2026"
    )
    assert "31 December 2026" in out and "compan" in out.lower()


def test_roman_urdu_company():
    out = bind_filing_dates(
        "", "company ki return ki last date?", [DEC, SEP], "TY2026", "roman_urdu"
    )
    assert "Companies ke liye return 31 December 2026" in out
    assert "September" not in out


def test_general_ask_gets_both():
    out = bind_filing_dates(
        "Filing is required.",
        "What is the filing deadline for all taxpayers?",
        [SEP, DEC],
        "TY2026",
    )
    assert "30 September 2026" in out and "31 December 2026" in out


def test_company_and_individual_ask_both():
    out = bind_filing_dates(
        "Individuals file by 30 September 2026.",
        "deadline for individuals and companies?",
        [SEP, DEC],
        "TY2026",
    )
    assert out.count("30 September") == 1 and "31 December 2026" in out


def test_no_dec31_in_sources_not_invented():
    out = bind_filing_dates("x", "company return deadline?", [SEP], "TY2026")
    assert "December" not in out


def test_non_filing_ask_untouched():
    assert bind_filing_dates("ok", "what is withholding on profit?", [DEC], "TY2026") == "ok"


def test_empty_strip_fallback_non_blank():
    assert plain_answer(
        "The due date is context mein mention nahi hai.", "roman_urdu", fallback=True
    ).strip()


def test_meta_does_not_specify_stripped():
    out = plain_answer(
        "Tax is 5%. The provided information does not specify the date.", "en", fallback=True
    )
    assert "does not specify" not in out
