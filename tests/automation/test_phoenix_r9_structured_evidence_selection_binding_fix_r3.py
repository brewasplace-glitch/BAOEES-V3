from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.autonomy.structured_product_evidence_acquisition import (
    _caller_repository_supports_structured_acquisition,
    _resolve_selections_for_acquisition,
    decide_routes,
    enhance_acquisition_result,
)

class R9StructuredEvidenceSelectionBindingFixR3Tests(unittest.TestCase):
    def test_supplied_register_overrides_empty_workspace_loader(self):
        supplied = {"selections": [{
            "requirement_id": "REQ-ROOF-STRUCTURE-STRUCTURAL-STEEL-SECTION",
            "element_role": "roof_structure",
            "material_family": "structural_steel_section",
        }]}
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            with patch(
                "phoenix.autonomy.structured_product_evidence_acquisition._load_selections",
                return_value=[],
            ) as loader:
                rows = _resolve_selections_for_acquisition(
                    ws, {"local_selection_register": supplied}
                )
                loader.assert_not_called()
        self.assertEqual(rows[0]["requirement_id"],
                         "REQ-ROOF-STRUCTURE-STRUCTURAL-STEEL-SECTION")
        routes = decide_routes(rows)
        self.assertEqual(routes[0]["requirement_id"],
                         "REQ-ROOF-STRUCTURE-STRUCTURAL-STEEL-SECTION")

    def test_temp_repository_without_provider_registry_does_not_run_live_search(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = root / "workspace"
            ws.mkdir()
            self.assertFalse(_caller_repository_supports_structured_acquisition(
                {"repository": root}
            ))
            base = {"status": "BLOCKED", "blockers": [{"reason": "BASE"}]}
            with patch(
                "phoenix.autonomy.structured_product_evidence_acquisition._provider_enabled",
                side_effect=AssertionError("live provider must not be consulted"),
            ):
                out = enhance_acquisition_result(
                    base,
                    kwargs={
                        "repository": root,
                        "workspace": ws,
                        "local_selection_register": {"selections": [{
                            "requirement_id": "REQ-REBAR",
                            "element_role": "reinforcement",
                            "material_family": "reinforcement_steel",
                        }]},
                    },
                )
            self.assertEqual(
                out["structured_product_evidence"]["reason"],
                "CALLER_REPOSITORY_PROVIDER_REGISTRY_NOT_CONFIGURED",
            )

    def test_configured_repository_is_eligible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg = root / "configs" / "phoenix" / "global_supplier_discovery_provider_registry_v1_0.json"
            reg.parent.mkdir(parents=True)
            reg.write_text("{}", encoding="utf-8")
            self.assertTrue(_caller_repository_supports_structured_acquisition(
                {"repository": root}
            ))

if __name__ == "__main__":
    unittest.main()
