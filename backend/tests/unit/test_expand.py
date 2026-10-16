from app.core.retrieval.expand import expand_parents
from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.sufficiency import ABSTAIN_SENTENCE, verified_band, web_is_sufficient


def hit(chunk_id: str, parent_id: str, text: str = "chunk") -> RankedHit:
    return RankedHit(chunk_id=chunk_id, payload={"parent_id": parent_id, "text": text})


def test_same_parent_is_included_once():
    blocks = expand_parents(
        [hit("c1", "s149"), hit("c2", "s149"), hit("c3", "s150")],
        {"s149": "section 149 text", "s150": "section 150 text"},
    )

    assert [block.parent_id for block in blocks] == ["s149", "s150"]
    assert blocks[0].text == "section 149 text"


def test_section_payload_is_prefixed_on_the_block():
    ranked = RankedHit(
        chunk_id="c1",
        payload={
            "parent_id": "s154A",
            "section": "154A",
            "section_title": "Export of Services",
            "text": "chargeable at 1 percent",
        },
    )
    blocks = expand_parents([ranked], {})
    assert blocks[0].text.startswith("Section 154A Export of Services.")
    assert "chargeable at 1 percent" in blocks[0].text


def test_missing_parent_falls_back_to_the_chunk():
    blocks = expand_parents([hit("c1", "missing", text="only the chunk")], {})

    assert blocks[0].text == "only the chunk"
    assert blocks[0].trimmed is False


def test_budget_trims_the_section_that_does_not_fit():
    # 4 characters count as 1 token.
    blocks = expand_parents(
        [hit("c1", "a"), hit("c2", "b")],
        {"a": "a" * 20, "b": "b" * 40},
        token_budget=8,
    )

    assert blocks[0].text == "a" * 20
    assert blocks[0].trimmed is False
    assert blocks[1].trimmed is True
    assert blocks[1].text == "b" * 12


def test_verified_band_and_web_floor():
    assert verified_band(0.8, sufficient_at=0.7, borderline_at=0.4) == "sufficient"
    assert verified_band(0.5, sufficient_at=0.7, borderline_at=0.4) == "borderline"
    assert verified_band(0.2, sufficient_at=0.7, borderline_at=0.4) == "insufficient"
    assert verified_band(None, sufficient_at=0.7, borderline_at=0.4) == "insufficient"
    assert web_is_sufficient(0.5) is True
    assert web_is_sufficient(0.49) is False
    assert "051-111-772-772" in ABSTAIN_SENTENCE
