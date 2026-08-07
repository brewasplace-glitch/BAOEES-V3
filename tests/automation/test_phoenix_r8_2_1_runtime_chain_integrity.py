from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from phoenix.autonomy.session_result_integrity_r821 import (
    SessionResultIntegrityError,
    prepare_adapter_result_path,
    validate_adapter_result_session,
)


class SessionResultIntegrityTests(unittest.TestCase):
    def test_prepare_removes_previous_mutable_summary(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "adapter_result.json"
            path.write_text('{"session_id":"OLD"}', encoding="utf-8")
            prepare_adapter_result_path(path)
            self.assertFalse(path.exists())

    def test_current_session_result_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "adapter_result.json"
            path.write_text(
                json.dumps({
                    "session_id": "PHX-CURRENT",
                    "capability_id": "structural_engineering",
                }),
                encoding="utf-8",
            )
            result = validate_adapter_result_session(
                path, "PHX-CURRENT", "structural_engineering"
            )
            self.assertEqual(result["session_id"], "PHX-CURRENT")

    def test_stale_session_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "adapter_result.json"
            path.write_text(
                json.dumps({
                    "session_id": "PHX-OLD",
                    "capability_id": "structural_engineering",
                }),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                SessionResultIntegrityError,
                "STALE_SESSION_ADAPTER_RESULT_REJECTED",
            ):
                validate_adapter_result_session(
                    path, "PHX-CURRENT", "structural_engineering"
                )

    def test_capability_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "adapter_result.json"
            path.write_text(
                json.dumps({
                    "session_id": "PHX-CURRENT",
                    "capability_id": "cost_planning",
                }),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                SessionResultIntegrityError,
                "SESSION_ADAPTER_CAPABILITY_MISMATCH",
            ):
                validate_adapter_result_session(
                    path, "PHX-CURRENT", "structural_engineering"
                )


class RuntimeChainSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[2]
        cls.chain_path = cls.repo / "phoenix" / "autonomy" / "structural_session_chain.py"
        cls.orchestrator_path = cls.repo / "phoenix" / "autonomy" / "session_orchestrator.py"
        cls.chain = cls.chain_path.read_text(encoding="utf-8")
        cls.orchestrator = cls.orchestrator_path.read_text(encoding="utf-8")

    def test_action_load_initialized_before_autonomous_solver_basis(self):
        init_pos = self.chain.index("action_load_for_solver=_read(v82_out)")
        first_use = self.chain.index("action_load_model=action_load_for_solver")
        self.assertLess(init_pos, first_use)
        self.assertEqual(self.chain.count("action_load_for_solver=_read(v82_out)"), 1)

    def test_v84_uses_same_remapped_action_load(self):
        self.assertIn(
            "_phoenix_build_autonomous_calculix_results(",
            self.chain,
        )
        v84_start = self.chain.index("_phoenix_build_autonomous_calculix_results(")
        v84_window = self.chain[v84_start:v84_start + 2500]
        self.assertIn("action_load_model=action_load_for_solver", v84_window)
        self.assertNotIn("action_load_model=_read(v82_out)", v84_window)

    def test_orchestrator_preclears_and_validates_adapter_result(self):
        root_pos = self.orchestrator.index(
            'adapter_root = workspace / "results" / "session_adapters" / cap_id'
        )
        prepare_pos = self.orchestrator.index(
            "_phx_r821_prepare_adapter_result_path", root_pos
        )
        validate_pos = self.orchestrator.index(
            "_phx_r821_validate_adapter_result_session", prepare_pos
        )
        persist_pos = self.orchestrator.index(
            "self._write_adapter_state(workspace, session, bootstrap, capability_states)",
            validate_pos,
        )
        self.assertLess(root_pos, prepare_pos)
        self.assertLess(prepare_pos, validate_pos)
        self.assertLess(validate_pos, persist_pos)


class RuntimeChainExecutionRegressionTests(unittest.TestCase):
    def test_v81_v82_basis_r81_r82_path_executes_without_unbound_action_load(self):
        import phoenix.autonomy.structural_session_chain as chain
        import phoenix.autonomy.autonomous_structural_topology_support_repair_v8_1_r81 as r81mod
        import phoenix.autonomy.autonomous_structural_interface_meshing_v8_1_r82 as r82mod

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            workspace = repo / "projects" / "runtime" / "PAT"
            out = workspace / "results" / "session_adapters" / "structural_engineering" / "validated_v8_1_to_v8_12"
            (repo / "runners").mkdir(parents=True)
            (repo / "configs" / "phoenix" / "structural").mkdir(parents=True)
            workspace.mkdir(parents=True)
            out.mkdir(parents=True)

            for _, runner_name in chain.STAGES:
                (repo / "runners" / runner_name).write_text("# test runner\n", encoding="utf-8")

            (repo / "configs" / "phoenix" / "structural" /
             "autonomous_structural_topology_support_repair_policy_r8_1.json").write_text(
                "{}", encoding="utf-8"
            )
            (repo / "configs" / "phoenix" / "structural" /
             "autonomous_structural_interface_meshing_policy_r8_2.json").write_text(
                "{}", encoding="utf-8"
            )

            v80 = repo / "v80.json"
            arch = repo / "arch.json"
            detail = repo / "detail.json"
            for p in (v80, arch, detail):
                p.write_text("{}", encoding="utf-8")

            base_model = {
                "nodes": [],
                "members": [],
                "shells": [],
                "supports": [],
            }
            base_actions = {"marker": "R82_BASE", "actions": [], "combinations": []}
            remapped_actions = {"marker": "R82_REMAPPED", "actions": [], "combinations": []}
            basis_seen = {}
            r82_seen = {}

            def fake_run_json(repository, runner, input_path, output_path, log_path):
                name = Path(runner).name
                Path(log_path).parent.mkdir(parents=True, exist_ok=True)
                Path(log_path).write_text("mock\n", encoding="utf-8")
                if name == chain.STAGES[0][1]:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_text(json.dumps(base_model), encoding="utf-8")
                    return 0
                if name == chain.STAGES[1][1]:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_text(json.dumps(base_actions), encoding="utf-8")
                    return 0
                if name == chain.STAGES[2][1]:
                    # Deliberately stop after the R8.2 path. The v8.3 input must
                    # already contain the remapped action model at this point.
                    return 99
                return 99

            def fake_basis(**kwargs):
                basis_seen["action"] = kwargs["action_load_model"]
                return {
                    "status": "PASSED",
                    "register": {"status": "PASSED"},
                    "structural_analysis_basis": {
                        "solver_basis": {
                            "basis": "TEST",
                            "analysis_type": "LINEAR_STATIC",
                            "materials": {},
                            "sections": {},
                        },
                        "element_assignments": {"by_id": {}, "by_type": {}},
                        "solver_adapters": ["calculix"],
                        "execution_policy": {"allow_execution": False},
                    },
                }

            r81_results = [
                {
                    "status": "BLOCKED",
                    "analytical_model": base_model,
                    "register": {
                        "status": "BLOCKED",
                        "blockers": [{"reason": "STRUCTURAL_LOAD_PATH_UNRESOLVED"}],
                    },
                    "blockers": [{"reason": "STRUCTURAL_LOAD_PATH_UNRESOLVED"}],
                },
                {
                    "status": "PASSED",
                    "analytical_model": base_model,
                    "register": {"status": "PASSED", "blockers": []},
                    "blockers": [],
                },
            ]

            def fake_r81(**kwargs):
                return r81_results.pop(0)

            def fake_r82(**kwargs):
                r82_seen["action"] = kwargs["action_load_model"]
                return {
                    "status": "PASSED",
                    "analytical_model": base_model,
                    "action_load_model": remapped_actions,
                    "register": {"status": "PASSED", "blockers": []},
                    "blockers": [],
                }

            def fake_section(candidates, name, required):
                if name == "action_load_input":
                    return ({
                        "basis": "TEST",
                        "unit_system": {},
                        "actions": [{"id": "G"}],
                        "combinations": [{"id": "C"}],
                    }, "TEST")
                if name == "structural_analysis_basis":
                    return (None, None)
                return (None, None)

            with mock.patch.object(chain, "build_v81_input", return_value=({}, {})), \
                 mock.patch.object(chain, "_run_json", side_effect=fake_run_json), \
                 mock.patch.object(chain, "_all_candidates", return_value=[]), \
                 mock.patch.object(chain, "_section", side_effect=fake_section), \
                 mock.patch.object(chain, "_phoenix_material_mode_structural_gate", return_value=False), \
                 mock.patch.object(chain, "_phoenix_build_autonomous_solver_basis", side_effect=fake_basis), \
                 mock.patch.object(chain, "selected_engineering_material_ids", return_value=set()), \
                 mock.patch.object(chain, "_phoenix_apply_solver_basis_to_analytical_model", return_value=(base_model, [])), \
                 mock.patch.object(chain, "_phoenix_normalize_support_candidates_for_solver", side_effect=lambda x: x), \
                 mock.patch.object(r81mod, "repair_structural_topology_for_solver", side_effect=fake_r81), \
                 mock.patch.object(r82mod, "repair_geometry_grounded_interfaces", side_effect=fake_r82):
                result = chain.run_structural_chain(
                    repository=repo,
                    session={"session_id": "PHX-TEST"},
                    workspace=workspace,
                    output_dir=out,
                    project_id="PAT",
                    v80_model_path=v80,
                    architectural_model_path=arch,
                    detailed_elements_path=detail,
                )

            self.assertEqual(basis_seen["action"]["marker"], "R82_BASE")
            self.assertEqual(r82_seen["action"]["marker"], "R82_BASE")
            v83_input = json.loads((out / "v8_3" / "input.json").read_text(encoding="utf-8"))
            self.assertEqual(v83_input["action_load_model"]["marker"], "R82_REMAPPED")
            self.assertEqual(result.status, "FAILED")
            self.assertEqual(result.next_stage, "8.3.0")


if __name__ == "__main__":
    unittest.main()
