from app.core.retrieval.fusion import RankedHit, fuse_hits, rrf_fuse


def test_shared_hit_outranks_a_single_list_leader():
    fused = rrf_fuse([["a", "b"], ["b", "c"]])
    ids = [chunk_id for chunk_id, _score in fused]

    assert ids == ["b", "a", "c"]
    assert fused[0][1] > fused[1][1] > fused[2][1]


def test_duplicate_id_inside_one_list_counts_once():
    fused = dict(rrf_fuse([["a", "a", "b"]]))

    assert fused["a"] == 1.0 / 61
    assert fused["b"] == 1.0 / 62


def test_domain_boost_can_change_the_order():
    other = RankedHit(chunk_id="other", domain="corporate_secp")
    income = RankedHit(chunk_id="income", domain="income_tax")
    ranked = fuse_hits([[other, income]], domain="income_tax", domain_boost=1.2)

    assert [hit.chunk_id for hit, _score in ranked] == ["income", "other"]


def test_no_domain_leaves_rrf_order():
    other = RankedHit(chunk_id="other", domain="corporate_secp")
    income = RankedHit(chunk_id="income", domain="income_tax")
    ranked = fuse_hits([[other, income]])

    assert [hit.chunk_id for hit, _score in ranked] == ["other", "income"]
