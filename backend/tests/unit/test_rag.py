import json

from app.agents.rag import RagRequest, run_qa
from app.core.budget import CallBudget
from app.core.ports import LLMResult
from app.core.retrieval.action_links import load_action_links
from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.sufficiency import ABSTAIN_SENTENCE

RULES = load_action_links("config/action_links.yaml")


def hit(chunk_id: str, text: str) -> RankedHit:
    return RankedHit(
        chunk_id=chunk_id,
        domain="income_tax",
        payload={"text": text, "parent_id": chunk_id},
    )


class LibrarySearch:
    def __init__(self, libraries: dict[str, list[RankedHit]]):
        self.libraries = libraries
        self.collections: list[str] = []

    async def __call__(self, *, collection: str, query: str, tax_year: str | None, k: int):
        self.collections.append(collection)
        return self.libraries.get(collection, [])


class ScriptedLLM:
    def __init__(self, answer: str, supported: bool = True):
        self.answer = answer
        self.supported = supported
        self.roles: list[str] = []
        self.systems: dict[str, str] = {}

    async def complete(self, role, messages, **kwargs):
        self.roles.append(role)
        self.systems[role] = messages[0].content
        if role == "judge":
            sentence = self.answer.strip()
            payload = {"sentences": [{"sentence": sentence, "supported": self.supported}]}
            text = json.dumps(payload)
        else:
            text = self.answer
        return LLMResult(text=text, model="fake/model", fallback=False, latency_ms=1)


def request() -> RagRequest:
    return RagRequest(
        question="How do I get an NTN?",
        search_query="section 149",
        language="en",
        tax_year="TY2027",
        corpus_date="2026-06-30",
    )


def score_library(mark: str):
    def score(_query: str, texts: list[str]) -> list[float]:
        if texts and mark in texts[0]:
            return [0.9]
        return [0.1 for _ in texts]

    return score


async def test_verified_library_answers_and_skips_the_web():
    search = LibrarySearch({"documents": [hit("s149", "verified law about NTN")]})
    llm = ScriptedLLM("You register for an NTN on IRIS [1].")
    budget = CallBudget()

    result = await run_qa(
        llm,
        search,
        score_library("verified"),
        request(),
        link_rules=RULES,
        budget=budget,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer_source == "verified"
    assert result.verified is True
    assert search.collections == ["documents"]
    assert llm.roles == ["reasoning", "judge"]
    assert budget.used == 2
    assert result.action_links[0].topic == "ntn_registration"


async def test_web_fallback_is_never_verified():
    search = LibrarySearch({"web_pages": [hit("web1", "official web page about NTN")]})
    llm = ScriptedLLM("Register on the website [1].")

    result = await run_qa(
        llm,
        search,
        score_library("official"),
        request(),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer_source == "web"
    assert result.verified is False
    assert search.collections == ["documents", "web_pages"]
    assert "official website" in llm.systems["reasoning"]


async def test_neither_library_abstains_without_an_llm_call():
    search = LibrarySearch(
        {
            "documents": [hit("s149", "unrelated")],
            "web_pages": [hit("web1", "also unrelated")],
        }
    )
    llm = ScriptedLLM("should not be called")
    budget = CallBudget()

    result = await run_qa(
        llm,
        search,
        score_library("no-such-mark"),
        request(),
        link_rules=RULES,
        budget=budget,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer_source == "none"
    assert result.answer == ABSTAIN_SENTENCE
    assert result.verified is False
    assert llm.roles == []
    assert budget.used == 0
    assert result.action_links[0].topic == "ntn_registration"
    assert [source.chunk_id for source in result.sources] == ["web1"]


class BandLLM:
    def __init__(self, grade: bool, broader: str, answer: str):
        self.grade = grade
        self.broader = broader
        self.answer = answer
        self.roles: list[str] = []
        self.users: list[str] = []
        self.fast = 0

    async def complete(self, role, messages, **kwargs):
        self.roles.append(role)
        self.users.append(messages[-1].content)
        if role == "fast":
            self.fast += 1
            text = json.dumps({"sufficient": self.grade}) if self.fast == 1 else self.broader
        elif role == "judge":
            payload = {"sentences": [{"sentence": self.answer.strip(), "supported": True}]}
            text = json.dumps(payload)
        else:
            text = self.answer
        return LLMResult(text=text, model="fake/model", fallback=False, latency_ms=1)


class QuerySearch:
    def __init__(self):
        self.queries: list[tuple[str, str]] = []

    async def __call__(self, *, collection: str, query: str, tax_year: str | None, k: int):
        self.queries.append((collection, query))
        if collection == "web_pages":
            return [hit("web", "official web page about NTN")]
        if "clear-win" in query:
            return [hit("strong", "verified law clearly answers NTN")]
        return [hit("weak", "maybe related to NTN")]


def band_score(_query: str, texts: list[str]) -> list[float]:
    text = texts[0] if texts else ""
    if "clearly" in text:
        return [0.95]
    if "official" in text:
        return [0.8]
    if "maybe" in text:
        return [0.55]
    return [0.1 for _ in texts]


async def test_borderline_grade_can_accept_the_verified_library():
    seen: list[str] = []

    def lookup(parent_ids: list[str]) -> dict[str, str]:
        seen.extend(parent_ids)
        return {parent_ids[0]: "full parent about NTN"}

    search = QuerySearch()
    llm = BandLLM(True, "unused", "Register for an NTN on IRIS [1].")

    result = await run_qa(
        llm,
        search,
        band_score,
        request(),
        sections=lookup,
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer_source == "verified"
    assert result.verified is True
    assert llm.fast == 1
    assert "web_pages" not in [collection for collection, _query in search.queries]
    assert "weak" in seen
    assert any("full parent about NTN" in user for user in llm.users)


async def test_failed_grade_retries_once_with_a_broader_query():
    search = QuerySearch()
    llm = BandLLM(False, "clear-win salary tax", "NTN is in the ordinance [1].")
    budget = CallBudget()

    result = await run_qa(
        llm,
        search,
        band_score,
        request(),
        link_rules=RULES,
        budget=budget,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer_source == "verified"
    assert llm.fast == 2
    assert budget.used == 4
    assert any("clear-win" in query for _collection, query in search.queries)
    assert "web_pages" not in [collection for collection, _query in search.queries]


async def test_failed_retry_uses_the_web_library_without_a_second_grade():
    search = QuerySearch()
    llm = BandLLM(False, "another vague query", "See the official page [1].")

    result = await run_qa(
        llm,
        search,
        band_score,
        request(),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer_source == "web"
    assert result.verified is False
    assert llm.fast == 2
    assert [role for role in llm.roles if role == "fast"] == ["fast", "fast"]
    assert "web_pages" in [collection for collection, _query in search.queries]
