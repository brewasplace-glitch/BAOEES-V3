from phoenix.architecture.r10_2_camera_quality_gate import QualityGatePolicy, evaluate_variant


def test_quality_gate_passes_complete_valid_view_set():
    policy = QualityGatePolicy(required_views=["street_corner", "rear", "side", "courtyard_or_patio", "aerial"])
    metrics = {
        "street_corner": {"visible_building_ratio": 0.45, "useful_context_ratio": 0.14, "occlusion_ratio": 0.20, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True},
        "rear": {"visible_building_ratio": 0.42, "useful_context_ratio": 0.12, "occlusion_ratio": 0.18, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True},
        "side": {"visible_building_ratio": 0.40, "useful_context_ratio": 0.11, "occlusion_ratio": 0.15, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True},
        "courtyard_or_patio": {"visible_building_ratio": 0.38, "useful_context_ratio": 0.11, "occlusion_ratio": 0.22, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True},
        "aerial": {"visible_building_ratio": 0.50, "useful_context_ratio": 0.18, "occlusion_ratio": 0.10, "camera_collision": False, "target_landmark_visible": True, "view_purpose_pass": True},
    }
    result = evaluate_variant(metrics, policy)
    assert result["overall_pass"] is True
    assert result["failures"] == {}


def test_quality_gate_fails_colliding_or_occluded_view():
    policy = QualityGatePolicy(required_views=["street_corner"])
    metrics = {
        "street_corner": {"visible_building_ratio": 0.20, "useful_context_ratio": 0.05, "occlusion_ratio": 0.80, "camera_collision": True, "target_landmark_visible": False, "view_purpose_pass": False}
    }
    result = evaluate_variant(metrics, policy)
    assert result["overall_pass"] is False
    assert "street_corner" in result["failures"]
