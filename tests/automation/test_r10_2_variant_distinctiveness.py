from phoenix.architecture.r10_2_optimizer import refine_variant


def test_refine_variant_preserves_distinct_variant_identity():
    identities = set()
    for code in ["A", "B", "C", "D", "E"]:
        refined = refine_variant(code, {"source_variant": code})
        identities.add(refined["variant_identity"])
    assert len(identities) == 5
