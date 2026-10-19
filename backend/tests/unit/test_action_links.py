"""Checks that an answer gets the official portal link for its topic."""

from pathlib import Path

from app.core.retrieval.action_links import load_action_links, match_action_links

RULES = Path("config/action_links.yaml")


def test_shipped_list_loads_and_skips_unconfirmed_urls():
    rules = load_action_links(RULES)

    assert {rule.topic for rule in rules} >= {"ntn_registration", "company_registration"}
    company = next(rule for rule in rules if rule.topic == "company_registration")
    assert company.url == ""

    links = match_action_links("secp company incorporation", rules)
    assert links == []


def test_keyword_match_returns_the_iris_link():
    links = match_action_links("How do I get an NTN?", load_action_links(RULES))

    assert [link.topic for link in links] == ["ntn_registration"]
    assert links[0].url == "https://iris.fbr.gov.pk/"
    assert links[0].authority == "FBR"


def test_domain_match_and_cap_of_three():
    rules = load_action_links(RULES)
    links = match_action_links(
        "filer return filing and ntn registration",
        rules,
        domains={"income_tax"},
    )

    assert len(links) == 3
    assert [link.topic for link in links] == [
        "ntn_registration",
        "return_filing",
        "active_taxpayer_list",
    ]


def test_keyword_does_not_match_inside_another_word():
    links = match_action_links("The atlas of tax history", load_action_links(RULES))

    assert links == []
