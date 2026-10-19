"""Checks that Roman Urdu tax talk becomes English search queries."""

from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.rewrite import (
    TOPICS,
    cross_reference_note,
    detect_topics,
    is_generic_web_hit,
    matching_topic_sections,
    rewrite_queries,
    rewrite_search_query,
    usable_web_hits,
)

Q1 = (
    "Yar maine 2 saal pehle 40 lakh ka ek plot liya tha ab majboori mein 55 lakh "
    "ka bech raha hoon. Transfer ke waqt mujh par tax lagega ya khareedne wale par? "
    "Aur jo upar ke 15 lakh bache hain us par FBR alag se tax mangega kya? Main filer "
    "toh hoon lekin is dafa return date guzarne ke baad late jama karwaya tha."
)
Q2 = (
    "Mera saga bhai Dubai mein job karta hai, usne mujhe wahan se bank account mein "
    "50 lakh rupay bheje hain taake main apne naam par gari le loon. Bank wale kehte "
    "hain bahar se aaye paison par koi tax nahi hota, lekin log dara rahe hain ke gari "
    "apne naam karwao ge toh FBR poochega paisa kahan se aaya. Asal baat kya hai aur "
    "mujhe bank se kaun sa kaghaz le kar rakhna chahiye?"
)
Q3 = (
    "Main ek private company mein job karta hoon, 1.5 lakh tankhwah hai aur office "
    "wale har mahine khud hi tax kaat lete hain. Ghar ka upar wala portion maine "
    "35 hazar mahana kiraye par diya hua hai. Iske ilawa har mahine mobile load, "
    "internet aur bijli ke bill par bhi tax kat-ta rehta hai. Kya kiraye ka hisab "
    "bhi FBR ko dena parega aur jo mobile/bijli par tax kata hai wo wapas mil sakta hai?"
)


def test_plot_and_late_filer_do_not_collapse_to_vehicle_tax():
    keys = {topic.key for topic in detect_topics(Q1)}
    joined = rewrite_search_query(Q1)

    assert keys == {"property", "late_filer", "capital_gain"}
    assert "236C" in joined
    assert "236K" in joined
    assert "Section 37" in joined
    assert "100BA" in joined
    assert "231B" not in joined


def test_remittance_and_car_stay_separate():
    keys = {topic.key for topic in detect_topics(Q2)}
    queries = rewrite_queries(Q2)

    assert keys == {"remittance", "vehicle"}
    assert any("111(4)" in query for query in queries)
    assert any("39(3)" in query for query in queries)
    assert any("231B" in query for query in queries)
    assert any("PRC" in query for query in queries)
    assert not any("149" in query and "salary" in query.lower() for query in queries)


def test_salary_rent_and_utility_are_three_subqueries():
    keys = {topic.key for topic in detect_topics(Q3)}
    queries = rewrite_queries(Q3)

    assert keys == {"salary", "rent", "utility"}
    assert len(queries) == 3
    assert any("149" in query for query in queries)
    assert any("Section 15" in query and "155" in query for query in queries)
    assert any("235" in query and "236" in query and "168" in query for query in queries)


def test_bechta_does_not_pull_property_tax():
    question = "Main online clothes bechta hoon EasyPaisa pe. NTN chahiye?"
    keys = {topic.key for topic in detect_topics(question)}

    assert "property" not in keys
    assert "capital_gain" not in keys
    assert "ntn" in keys
    rewritten = rewrite_search_query(question)
    assert "181" in rewritten
    assert "236C" not in rewritten
    assert "236K" not in rewritten


def test_plot_sale_still_matches_property():
    keys = {topic.key for topic in detect_topics("Main plot bech raha hoon 40 lakh ka")}
    assert "property" in keys


def test_cash_withdrawal_does_not_take_the_property_note():
    question = "What is the filer vs non-filer withholding on a cash withdrawal of Rs 50000?"
    direct = cross_reference_note(f"{question} {rewrite_search_query(question)}")
    assert "236C" not in direct
    assert "15 lakh" not in direct
    capital = next(topic.query for topic in TOPICS if topic.key == "capital_gain")
    injected = cross_reference_note(f"{question} {capital}")
    assert "236C" not in injected
    assert "236K" not in injected
    assert "15 lakh" not in injected


def test_existing_mappings_still_fire():
    assert "154A" in rewrite_search_query("freelancer upwork", "export income")
    assert "181" in rewrite_search_query("NTN lena hoga", "online clothes")
    assert "122" in rewrite_search_query("Mujhe FBR notice mila hai", "notice")
    assert "231AB" in rewrite_search_query("cash withdrawal from bank", "")


def test_raw_roman_urdu_is_not_sent_to_qdrant_when_topics_exist():
    queries = rewrite_queries(Q1, Q1)
    assert Q1 not in queries
    assert all(
        "Section" in query or "section" in query.lower() or "ATL" in query for query in queries
    )


def test_homepage_web_hits_are_dropped():
    home = RankedHit(
        chunk_id="web1",
        payload={
            "title": "Federal Board of Revenue",
            "source_url": "https://fbr.gov.pk/",
            "text": "Stay Connected",
        },
    )
    statute = RankedHit(
        chunk_id="s236c",
        payload={"section": "236C", "text": "seller advance tax on immovable property"},
    )
    assert is_generic_web_hit(home) is True
    assert usable_web_hits([(home, 0.9)]) == []
    assert matching_topic_sections([statute], Q1) == {"236C"}


Q4 = (
    "Meri walida senior citizen hain, unke bank profit aur Behbood Savings "
    "Certificates par tax kat-ta hai kya?"
)


def test_cross_reference_notes_follow_the_triggered_topics():
    plot = cross_reference_note(Q1)
    assert "236C" in plot and "236K" in plot and "37(1A)" in plot and "100BA" in plot
    remit = cross_reference_note(Q2)
    assert "111(4)" in remit and "5 million" in remit and "PRC" in remit
    assert "39(3)" in remit and "231B" in remit
    income = cross_reference_note(Q3)
    assert "149" in income and "155" in income and "168" in income and "170" in income
    assert "non-adjustable" in income
    senior = {topic.key for topic in detect_topics(Q4)}
    assert "senior_profit" in senior
    assert "capital_gain" not in senior
    assert cross_reference_note(Q4) == ""


def test_plot_search_query_does_not_pull_income_lines():
    blob = f"{Q1} {rewrite_search_query(Q1)}"
    keys = {topic.key for topic in detect_topics(blob)}
    note = cross_reference_note(blob, language="roman_urdu")

    assert keys == {"property", "late_filer", "capital_gain"}
    assert "236C" in note and "236K" in note and "37(1A)" in note and "100BA" in note
    assert "149" not in note
    assert "155" not in note
    assert "235" not in note
    lowered = note.lower()
    assert "tankhwah" not in lowered
    assert "kiraya" not in lowered
    assert "bijli" not in lowered
    assert "salary" not in lowered
    assert "electricity" not in lowered
    assert "mobile" not in lowered


FREELANCER = (
    "Main Upwork pe freelancer hoon, foreign clients ko IT services deta hoon. "
    "Kitna tax banta hai aur kaun si section?"
)


def test_freelancer_note_names_154a_and_114_without_income_sections():
    blob = f"{FREELANCER} {rewrite_search_query(FREELANCER)}"
    keys = {topic.key for topic in detect_topics(blob)}
    note = cross_reference_note(blob, language="roman_urdu")

    assert keys == {"freelancer"}
    assert "154A" in note
    assert "114" in note
    assert "149" not in note
    assert "155" not in note
    assert "235" not in note
