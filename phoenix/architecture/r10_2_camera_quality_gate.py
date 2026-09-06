from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
import json
from pathlib import Path


@dataclass
class QualityGatePolicy:
    required_views: List[str]
    visible_building_ratio_min: float = 0.35
    useful_context_ratio_min: float = 0.10
    occlusion_ratio_max: float = 0.40
    require_camera_collision_false: bool = True
    require_target_landmark_visible: bool = True
    require_view_purpose_pass: bool = True
    max_attempts_per_view: int = 5
    auto_reframe: bool = True
    auto_retarget: bool = True

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "QualityGatePolicy":
        thresholds = payload.get("thresholds", {})
        required = payload.get("booleans_required", {})
        retry = payload.get("retry_policy", {})
        return cls(
            required_views=list(payload.get("required_views", [])),
            visible_building_ratio_min=float(thresholds.get("visible_building_ratio_min", 0.35)),
            useful_context_ratio_min=float(thresholds.get("useful_context_ratio_min", 0.10)),
            occlusion_ratio_max=float(thresholds.get("occlusion_ratio_max", 0.40)),
            require_camera_collision_false=bool(required.get("camera_collision", True)),
            require_target_landmark_visible=bool(required.get("target_landmark_visible", True)),
            require_view_purpose_pass=bool(required.get("view_purpose_pass", True)),
            max_attempts_per_view=int(retry.get("max_attempts_per_view", 5)),
            auto_reframe=bool(retry.get("auto_reframe", True)),
            auto_retarget=bool(retry.get("auto_retarget", True)),
        )


def load_policy(path: str | Path) -> QualityGatePolicy:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return QualityGatePolicy.from_dict(data)


@dataclass
class ViewMetrics:
    visible_building_ratio: float
    useful_context_ratio: float
    occlusion_ratio: float
    camera_collision: bool
    target_landmark_visible: bool
    view_purpose_pass: bool
    notes: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ViewMetrics":
        return cls(
            visible_building_ratio=float(payload.get("visible_building_ratio", 0.0)),
            useful_context_ratio=float(payload.get("useful_context_ratio", 0.0)),
            occlusion_ratio=float(payload.get("occlusion_ratio", 1.0)),
            camera_collision=bool(payload.get("camera_collision", True)),
            target_landmark_visible=bool(payload.get("target_landmark_visible", False)),
            view_purpose_pass=bool(payload.get("view_purpose_pass", False)),
            notes=list(payload.get("notes", [])),
        )


def evaluate_view(view_name: str, metrics: ViewMetrics, policy: QualityGatePolicy) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if metrics.visible_building_ratio < policy.visible_building_ratio_min:
        reasons.append(f"visible_building_ratio below threshold for {view_name}")
    if metrics.useful_context_ratio < policy.useful_context_ratio_min:
        reasons.append(f"useful_context_ratio below threshold for {view_name}")
    if metrics.occlusion_ratio > policy.occlusion_ratio_max:
        reasons.append(f"occlusion_ratio above threshold for {view_name}")
    if policy.require_camera_collision_false and metrics.camera_collision:
        reasons.append(f"camera_collision detected for {view_name}")
    if policy.require_target_landmark_visible and not metrics.target_landmark_visible:
        reasons.append(f"target_landmark_visible failed for {view_name}")
    if policy.require_view_purpose_pass and not metrics.view_purpose_pass:
        reasons.append(f"view_purpose_pass failed for {view_name}")
    if view_name == "courtyard_or_patio" and not metrics.view_purpose_pass:
        reasons.append("courtyard_or_patio does not clearly communicate courtyard/patio space")
    reasons.extend(metrics.notes)
    return (len(reasons) == 0, reasons)


def evaluate_variant(view_metrics: Dict[str, Dict[str, Any]], policy: QualityGatePolicy) -> Dict[str, Any]:
    missing = [view for view in policy.required_views if view not in view_metrics]
    passed_views: Dict[str, bool] = {}
    failures: Dict[str, List[str]] = {}
    for view_name in policy.required_views:
        if view_name not in view_metrics:
            passed_views[view_name] = False
            failures[view_name] = ["missing required view metrics"]
            continue
        metrics = ViewMetrics.from_dict(view_metrics[view_name])
        passed, reasons = evaluate_view(view_name, metrics, policy)
        passed_views[view_name] = passed
        if not passed:
            failures[view_name] = reasons
    if missing:
        failures["missing_views"] = missing
    overall_pass = all(passed_views.get(v, False) for v in policy.required_views)
    return {
        "overall_pass": overall_pass,
        "passed_views": passed_views,
        "failures": failures,
        "required_views": list(policy.required_views),
    }
