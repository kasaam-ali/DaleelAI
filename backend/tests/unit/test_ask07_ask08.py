from app.agents.rag import RagRequest, statute_note
from app.core.retrieval.rewrite import detect_topics, rewrite_queries

ASK07 = "Does the TY2026 section 4AB salary surcharge still apply in TY2027?"
ASK08 = "My only income is Rs 400,000 salary — do I still need to file a return?"


def test_ask07_4ab_says_no_for_ty2027():
    note = statute_note(RagRequest(question=ASK07, search_query=ASK07, language="en", tax_year="TY2027", corpus_date="2026-10-14"))
    assert "TY2026" in note and "9%" in note
    assert "No, it does not apply in TY2027" in note


def test_ask08_routes_to_filing():
    assert "return_filing" in {t.key for t in detect_topics(ASK08)}
    assert any("Section 114" in q for q in rewrite_queries(ASK08))
