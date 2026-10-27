from app.core.deadline_binder import _FILING_ASK, bind_filing_dates
from app.core.retrieval.rewrite import detect_topics, rewrite_queries

SRC = [
    "118. Method of furnishing returns ... (a) in the case of a company, on or before the "
    "thirty-first day of December next following the end of the tax year; "
    "(b) in any other case, on or before the thirtieth day of September."
]
RU_Q = "TY2027 ki return ki last date individuals aur companies ke liye kya hai?"


def test_ru_filing_ask_binds_both_dates():
    out = bind_filing_dates("Yeh baat sources se clear nahi.", RU_Q, SRC, "TY2027", "roman_urdu")
    assert "30 September 2027" in out and "31 December 2027" in out
    assert "Companies ke liye" in out and "clear nahi" not in out


def test_ru_phrasings_match_filing_ask():
    for q in ("Companies ki return kab tak deni hai?", "IRIS pe return ki aakhri tareek?"):
        assert _FILING_ASK.search(q)


def test_ru_filing_hits_return_filing_topic():
    for q in (
        RU_Q,
        "Companies aur individuals ki return kab tak file karni hai?",
        "tax return ki akhri tareekh kya hai",
    ):
        assert "return_filing" in [t.key for t in detect_topics(q)], q
    assert any("118" in q for q in rewrite_queries(RU_Q))
