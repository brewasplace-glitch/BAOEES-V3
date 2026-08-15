from __future__ import annotations

import json
import unittest
from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = project_root()
POLICY = ROOT / "configs" / "phoenix" / "official_start_layout_cleanup_policy_v1_1.json"
LAYOUT_TEST = ROOT / "tests" / "automation" / "test_phoenix_official_start_layout_cleanup_v1_1.py"


class LayoutCleanupR2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8-sig"))
        cls.test_source = LAYOUT_TEST.read_text(encoding="utf-8")

    def test_01_policy_version_is_1_1_1(self) -> None:
        self.assertEqual("1.1.1", self.policy["policy_version"])

    def test_02_fixed_revision_is_r2(self) -> None:
        self.assertEqual("R2", self.policy["fixed_revision"])

    def test_03_layout_test_expects_1_1_1(self) -> None:
        self.assertIn('self.assertEqual("1.1.1", self.policy["policy_version"])', self.test_source)

    def test_04_layout_test_no_longer_expects_1_1_0(self) -> None:
        self.assertNotIn('self.assertEqual("1.1.0", self.policy["policy_version"])', self.test_source)

    def test_05_r2_does_not_change_ui_contract(self) -> None:
        self.assertFalse(self.policy["fixed_r2"]["ui_changed"])
        self.assertFalse(self.policy["fixed_r2"]["regression_contract_changed"])


if __name__ == "__main__":
    unittest.main()
