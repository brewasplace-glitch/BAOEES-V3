from phoenix.architecture.r10_2_optimizer import build_evaluation_summary, refine_variant


def test_result_contract_keeps_preliminary_status_and_locks():
    refined = refine_variant("A", {"source_variant": "A"})
    summary = build_evaluation_summary("A", refined)
    assert refined["design_status"] == "PRELIMINARY / NOT FOR CONSTRUCTION"
    assert refined["locks"]["design_selection"] == "LOCKED"
    assert summary["status"] == "READY_FOR_R10_2_VISUAL_AND_QA_PIPELINE"
