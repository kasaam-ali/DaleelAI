"""Checks TAX_SYNONYMS expansion and the cap on added terms."""

from app.core.retrieval.synonyms import added_terms, expand_search_query


def test_salary_adds_synonyms_without_repeating_itself():
    added = added_terms("salary tax")

    assert "salary" not in added
    assert added == ["wages", "remuneration", "pay", "earnings"]


def test_income_alone_does_not_pull_in_salary_terms():
    # "income tax return" was expanded with salary words, which routed to s.12/s.149.
    assert "salary" not in added_terms("deadline to file my income tax return")


def test_match_is_whole_word_and_case_insensitive():
    assert added_terms("salaryman") == []
    assert "wages" in added_terms("SALARY")


def test_two_groups_stop_at_six_added_terms():
    added = added_terms("salary and property")

    assert len(added) == 6
    assert added[:4] == ["wages", "remuneration", "pay", "earnings"]
    assert added[4:] == ["real estate", "immovable property"]
    assert "land" not in added


def test_unknown_words_leave_the_query_unchanged():
    assert expand_search_query("section 149") == "section 149"


def test_expanded_query_keeps_the_original_text_first():
    assert added_terms("Petrol levy")[:1] == ["diesel"]
    assert len(added_terms("Petrol levy")) == 6

    expanded = expand_search_query("Petrol levy")

    assert expanded.startswith("Petrol levy ")
    assert "diesel" in expanded
