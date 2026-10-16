import asyncio
import json

from app.agents.rag import RagRequest, run_qa
from app.core.budget import CallBudget
from app.core.ports import LLMResult
from app.core.retrieval.action_links import load_action_links
from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.rewrite import rewrite_search_query
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
    assert set(search.collections) == {"documents"}
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
    assert "documents" in search.collections
    assert "web_pages" in search.collections
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


async def test_statutory_documents_beat_generic_web_homepages():
    documents = RankedHit(
        chunk_id="s236c",
        payload={
            "section": "236C",
            "parent_id": "s236c",
            "text": "seller advance tax on immovable property",
        },
    )
    homepage = RankedHit(
        chunk_id="home",
        payload={
            "title": "Federal Board of Revenue",
            "source_url": "https://fbr.gov.pk/",
            "parent_id": "home",
            "text": "Stay Connected Facebook",
        },
    )
    search = LibrarySearch({"documents": [documents], "web_pages": [homepage]})
    llm = ScriptedLLM("Seller pays section 236C [1].")

    result = await run_qa(
        llm,
        search,
        lambda _query, texts: [0.2 for _ in texts],
        RagRequest(
            question="plot bech raha hoon 40 lakh",
            search_query="plot sale",
            language="roman_urdu",
            tax_year="TY2027",
            corpus_date="2026-06-30",
        ),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer_source == "verified"
    assert "236C" in result.answer or "Seller" in result.answer
    assert "web_pages" not in search.collections


def _statute(chunk_id: str, section: str, text: str) -> RankedHit:
    return RankedHit(
        chunk_id=chunk_id,
        payload={"section": section, "parent_id": chunk_id, "text": text},
    )


async def test_labeled_statutes_skip_the_cross_encoder():
    documents = [
        _statute("s236c", "236C", "seller advance tax"),
        _statute("s236k", "236K", "buyer advance tax"),
        _statute("s37", "37", "capital gain holding period"),
        _statute("s100", "100BA", "tenth schedule higher withholding"),
    ]
    search = LibrarySearch({"documents": documents})
    calls: list[list[str]] = []

    def score(_query: str, texts: list[str]) -> list[float]:
        calls.append(texts)
        return [0.1 for _ in texts]

    result = await run_qa(
        ScriptedLLM("Seller pays section 236C [1]."),
        search,
        score,
        RagRequest(
            question="plot bech raha hoon late filer hoon 15 lakh munafa",
            search_query="plot sale late filer capital gain",
            language="roman_urdu",
            tax_year="TY2027",
            corpus_date="2026-06-30",
        ),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert calls == []
    assert search.collections == ["documents"]
    assert result.answer_source == "verified"
    assert {hit.payload["section"] for hit in result.sources} == {"236C", "236K", "37", "100BA"}


async def test_missing_statute_still_reranks_a_short_opening():
    long = "SALARY " + ("x" * 2000)
    search = LibrarySearch({"documents": [_statute("s149", "149", long)]})
    seen: list[str] = []

    def score(_query: str, texts: list[str]) -> list[float]:
        seen.extend(texts)
        return [0.2 for _ in texts]

    await run_qa(
        ScriptedLLM("Section 149 salary withholding [1]."),
        search,
        score,
        RagRequest(
            question="Meri tankhwah par kitna tax hai?",
            search_query="salary income Section 149",
            language="roman_urdu",
            tax_year="TY2027",
            corpus_date="2026-06-30",
        ),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert seen
    assert all(text.startswith("SALARY ") and len(text) <= 400 for text in seen)


async def test_property_note_is_spoken_without_a_model_or_rerank():
    search = LibrarySearch({"documents": [_statute("s236c", "236C", "seller advance tax")]})
    seen: list[str] = []
    llm = ScriptedLLM("should not be called")

    def score(_query: str, texts: list[str]) -> list[float]:
        seen.extend(texts)
        return [0.2 for _ in texts]

    question = (
        "Main plot bech raha hoon 40 lakh ka, 15 lakh munafa hai, "
        "2 saal pehle kharida, late filer hoon. Seller aur buyer ka tax?"
    )
    result = await run_qa(
        llm,
        search,
        score,
        RagRequest(
            question=question,
            search_query=rewrite_search_query(question),
            language="roman_urdu",
            tax_year="TY2027",
            corpus_date="2026-06-30",
        ),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert seen == []
    assert llm.roles == []
    assert search.collections == ["documents"]
    assert "236C" in result.answer
    assert "236K" in result.answer
    assert "37(1A)" in result.answer
    assert "100BA" in result.answer
    assert "zero" in result.answer.lower()
    assert "149" not in result.answer
    assert "155" not in result.answer
    assert "235" not in result.answer


async def test_freelancer_note_is_spoken_without_a_model_or_rerank():
    search = LibrarySearch({"documents": [_statute("s154", "154A", "export of IT services")]})
    seen: list[str] = []
    llm = ScriptedLLM("should not be called")

    def score(_query: str, texts: list[str]) -> list[float]:
        seen.extend(texts)
        return [0.2 for _ in texts]

    question = (
        "Main Upwork pe freelancer hoon, foreign clients ko IT services deta hoon. "
        "Kitna tax banta hai aur kaun si section?"
    )
    result = await run_qa(
        llm,
        search,
        score,
        RagRequest(
            question=question,
            search_query=rewrite_search_query(question),
            language="roman_urdu",
            tax_year="TY2027",
            corpus_date="2026-06-30",
        ),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert seen == []
    assert llm.roles == []
    assert search.collections == ["documents"]
    assert "154A" in result.answer
    assert "114" in result.answer
    assert "149" not in result.answer
    assert "155" not in result.answer
    assert "235" not in result.answer


async def test_local_web_page_speaks_the_note_without_the_model():
    page = RankedHit(
        chunk_id="web154",
        payload={
            "title": "Export of IT services",
            "source_url": "https://fbr.gov.pk/categ/income-tax/51147/1",
            "text": "Section 154A withholding on export of services",
        },
    )
    search = LibrarySearch({"documents": [], "web_pages": [page]})
    llm = ScriptedLLM("should not be called")
    question = "Main Upwork pe freelancer hoon, foreign clients ko IT services deta hoon."

    result = await run_qa(
        llm,
        search,
        lambda _query, texts: [0.2 for _ in texts],
        RagRequest(
            question=question,
            search_query=rewrite_search_query(question),
            language="roman_urdu",
            tax_year="TY2027",
            corpus_date="2026-06-30",
        ),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert llm.roles == []
    assert search.collections == ["documents", "web_pages"]
    assert "154A" in result.answer
    assert "114" in result.answer
    assert result.answer_source == "web"


async def test_empty_local_indexes_fall_through_without_a_note():
    search = LibrarySearch({"documents": [], "web_pages": []})
    llm = ScriptedLLM("should not be called")

    result = await run_qa(
        llm,
        search,
        lambda _query, texts: [0.2 for _ in texts],
        request(),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer == ABSTAIN_SENTENCE
    assert llm.roles == []
    assert "documents" in search.collections


async def test_fast_path_status_precedes_the_note():
    search = LibrarySearch({"documents": [_statute("s154", "154A", "export of IT services")]})
    order: list[str] = []

    async def on_status(node: str) -> None:
        order.append(node)

    async def on_delta(text: str) -> None:
        order.append(text)
        assert search.collections == []

    question = "Main Upwork pe freelancer hoon"
    await run_qa(
        ScriptedLLM("should not be called"),
        search,
        lambda _query, texts: [0.2 for _ in texts],
        RagRequest(
            question=question,
            search_query="section 154A export of IT services",
            language="roman_urdu",
            tax_year="TY2027",
            corpus_date="2026-06-30",
        ),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
        on_status=on_status,
        on_delta=on_delta,
    )

    assert order[0] == "retrieve"
    assert "154A" in order[1]
    assert "114" in order[1]


async def test_freelancer_note_is_not_delayed_by_search():
    release = asyncio.Event()

    class BlockingSearch:
        def __init__(self) -> None:
            self.calls = 0

        async def __call__(self, *, collection: str, query: str, tax_year: str | None, k: int):
            self.calls += 1
            await release.wait()
            return []

    search = BlockingSearch()
    spoken = asyncio.Event()

    async def on_delta(text: str) -> None:
        assert search.calls == 0
        assert "154A" in text and "114" in text
        spoken.set()

    question = (
        "Main Upwork pe freelancer hoon, foreign clients ko IT services deta hoon. "
        "Kitna tax banta hai aur kaun si section?"
    )
    task = asyncio.create_task(
        run_qa(
            ScriptedLLM("should not be called"),
            search,
            lambda _query, texts: [0.2 for _ in texts],
            RagRequest(
                question=question,
                search_query=rewrite_search_query(question),
                language="roman_urdu",
                tax_year="TY2027",
                corpus_date="2026-06-30",
            ),
            link_rules=RULES,
            sufficient_at=0.7,
            borderline_at=0.4,
            on_delta=on_delta,
        )
    )
    await asyncio.wait_for(spoken.wait(), timeout=1)
    release.set()
    result = await task
    assert "154A" in result.answer and "114" in result.answer
    assert search.calls >= 1
