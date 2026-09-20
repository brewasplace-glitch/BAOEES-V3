import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy import (
    AdapterSynthesisService,
    DisabledIsolationProvider,
    UniversalCapabilityExecutorRegistry,
)


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs/phoenix"


def load(name):
    return json.loads((CFG / name).read_text(encoding="utf-8"))


def candidate(
    engine_id="future.phase8.demo",
    adapter_id="future.phase8.demo.adapter",
    *,
    mutating=False,
):
    action = "documentation.update" if mutating else "research.inspect"
    domain = "software" if mutating else "research"
    obj = {
        "schema": "PHOENIX_ENGINE_CANDIDATE_MANIFEST_V1",
        "engine_id": engine_id,
        "display_name": "Phase 8 Demo",
        "mutation_capable": mutating,
        "gateway_required": mutating,
        "allowed_actions": [action],
        "allowed_domains": [domain],
        "action_profiles": [
            {
                "action": action,
                "risk": "LOW",
                "domain": domain,
                "mutating": mutating,
                "plan_dispatchable": True,
            }
        ],
        "adapters": [
            {
                "adapter_id": adapter_id,
                "actions": [action],
                "kind": "callable_scaffold",
                "mutation_capable": mutating,
                "gateway_required": mutating,
                "plan_dispatchable": True,
                "priority": 100,
            }
        ],
        "metadata": {"test": True},
    }
    if mutating:
        obj["allowed_path_roots"] = ["docs/automation/autonomous_generated/"]
    return obj


class Phase8Tests(unittest.TestCase):
    def service_and_proposal(self, td, *, mutating=False):
        service = AdapterSynthesisService(ROOT, Path(td))
        proposal = service.onboarding.build_proposal(
            candidate(mutating=mutating), persist=True
        )
        adapter_id = proposal["executor_registry_patch"][0]["adapter_id"]
        return service, proposal, adapter_id

    def candidate_record(self, td):
        service, proposal, adapter_id = self.service_and_proposal(td)
        record = service.build_candidate(
            Path(proposal["runtime_path"]), adapter_id, persist=True
        )
        return service, proposal, record

    def attestation(self, td):
        service, proposal, record = self.candidate_record(td)
        attestation = service.verify_candidate(
            Path(record["runtime_path"]), persist=True
        )
        return service, proposal, record, attestation

    def test_phase8_policy_active_fail_closed(self):
        policy = load("adapter_synthesis_policy_v1.json")
        self.assertEqual(policy["status"], "ACTIVE")
        self.assertTrue(policy["fail_closed"])
        self.assertEqual(
            policy["synthesis"]["mutation_capable_adapter_synthesis"], "DENY"
        )
        self.assertFalse(policy["synthesis"]["repository_write_during_synthesis"])

    def test_verification_profile_is_static_only(self):
        profile = load("adapter_verification_profile_v1.json")
        self.assertEqual(profile["status"], "ACTIVE_STATIC_ONLY")
        self.assertFalse(profile["candidate_execution_enabled"])
        self.assertFalse(profile["active_provider"]["security_boundary"])

    def test_open_source_review_disables_mxc(self):
        review = load("open_source_adapter_synthesis_verification_review_v1.json")
        mxc = review["windows_isolation_candidates"][0]
        self.assertEqual(mxc["name"], "Microsoft eXecution Container (MXC)")
        self.assertEqual(mxc["decision"], "DISABLED")
        self.assertFalse(review["phase8_decision"]["candidate_code_execution"])

    def test_policy_versions_advance(self):
        self.assertGreaterEqual(load("autonomy_policy_v2.json")["version"], "2.6.0")
        self.assertGreaterEqual(load("engine_registry_v1.json")["version"], "1.7.0")
        self.assertGreaterEqual(
            load("capability_executor_registry_v1.json")["version"], "1.4.0"
        )
        self.assertGreaterEqual(
            load("future_engine_admission_contract_v1.json")["version"], "1.5.0"
        )

    def test_phase8_engine_registered_and_gateway_bound(self):
        registry = load("engine_registry_v1.json")
        engine = [
            x
            for x in registry["engines"]
            if x["engine_id"] == "autonomy.adapter_synthesis"
        ][0]
        self.assertTrue(engine["mutation_capable"])
        self.assertTrue(engine["gateway_required"])
        self.assertEqual(engine["allowed_path_roots"], ["runtime://adapter_synthesis/"])

    def test_phase8_internal_adapter_covers_actions(self):
        registry = load("capability_executor_registry_v1.json")
        adapter = [
            x
            for x in registry["adapters"]
            if x["adapter_id"] == "builtin.adapter.synthesis.internal"
        ][0]
        self.assertFalse(adapter["plan_dispatchable"])
        self.assertEqual(adapter["implementation"], "internal.gateway_managed")
        self.assertEqual(len(adapter["actions"]), 3)

    def test_registry_coverage_remains_complete(self):
        report = UniversalCapabilityExecutorRegistry.from_repo(ROOT).coverage_report()
        self.assertTrue(report["complete"])
        self.assertEqual(
            report["active_engine_actions"], report["covered_engine_actions"]
        )
        self.assertGreaterEqual(report["active_engines"], 9)

    def test_attestation_schema_is_draft_2020_12(self):
        schema = load("adapter_runtime_attestation_v1.schema.json")
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIn("candidate_code_executed", schema["required"])

    def test_read_only_candidate_synthesis_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            service, proposal, adapter_id = self.service_and_proposal(td)
            descriptor = proposal["executor_registry_patch"][0]
            spec1, source1 = service.synthesizer.synthesize(
                engine_id=proposal["engine_id"], descriptor=descriptor
            )
            spec2, source2 = service.synthesizer.synthesize(
                engine_id=proposal["engine_id"], descriptor=descriptor
            )
            self.assertEqual(spec1, spec2)
            self.assertEqual(source1, source2)
            self.assertNotIn("NotImplementedError", source1)
            self.assertIn(adapter_id, source1)

    def test_candidate_passes_phase7_static_contract(self):
        with tempfile.TemporaryDirectory() as td:
            service, _, record = self.candidate_record(td)
            self.assertEqual(record["status"], "SYNTHESIZED_STATIC_VALIDATION_PASS")
            self.assertTrue(record["static_validation"]["activation_ready"])
            self.assertFalse(record["candidate_code_executed"])
            self.assertFalse(record["repository_write_performed"])
            self.assertRegex(record["source_sha256"], r"^[a-f0-9]{64}$")

    def test_mutation_capable_candidate_synthesis_denied(self):
        with tempfile.TemporaryDirectory() as td:
            service, proposal, adapter_id = self.service_and_proposal(
                td, mutating=True
            )
            with self.assertRaisesRegex(
                PermissionError, "MUTATION_CAPABLE_SYNTHESIS_DENY"
            ):
                service.build_candidate(
                    Path(proposal["runtime_path"]), adapter_id, persist=False
                )

    def test_candidate_source_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            service, _, record = self.candidate_record(td)
            source = Path(record["source_path"])
            source.write_text(source.read_text() + "# tamper\n", encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "source integrity"):
                service.load_candidate(Path(record["runtime_path"]))

    def test_candidate_record_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            service, _, record = self.candidate_record(td)
            path = Path(record["runtime_path"])
            obj = json.loads(path.read_text())
            obj["automatic_activation"] = True
            path.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "HMAC"):
                service.load_candidate(path)

    def test_tampered_phase6_proposal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            service, proposal, adapter_id = self.service_and_proposal(td)
            path = Path(proposal["runtime_path"])
            obj = json.loads(path.read_text())
            obj["engine_id"] = "tampered.engine"
            path.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "HMAC"):
                service.build_candidate(path, adapter_id, persist=False)

    def test_attestation_is_complete_and_nonexecuting(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, record, attestation = self.attestation(td)
            self.assertEqual(
                attestation["status"], "STATIC_VERIFIED_EXECUTION_BLOCKED"
            )
            self.assertFalse(attestation["candidate_code_executed"])
            self.assertFalse(attestation["repository_write_performed"])
            self.assertFalse(attestation["phase7_activation_transaction_eligible"])
            self.assertEqual(attestation["deterministic_replay"]["status"], "PASS")
            self.assertEqual(attestation["source_sha256"], record["source_sha256"])
            self.assertEqual(
                attestation["stdout_sha256"], hashlib.sha256(b"").hexdigest()
            )

    def test_disabled_provider_refuses_execution(self):
        provider = DisabledIsolationProvider("test")
        with self.assertRaisesRegex(PermissionError, "NO_ACCEPTED_SECURITY_BOUNDARY"):
            provider.execute("pass", {})

    def test_static_replay_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            service, proposal, adapter_id = self.service_and_proposal(td)
            descriptor = proposal["executor_registry_patch"][0]
            _, source = service.synthesizer.synthesize(
                engine_id=proposal["engine_id"], descriptor=descriptor
            )
            validation = service.phase7_validator.validate(
                source, engine_id=proposal["engine_id"], descriptor=descriptor
            )
            report = service.static_verifier.verify(
                source + "# altered\n", source, validation
            )
            self.assertEqual(report.status, "STATIC_FAIL")
            self.assertIn("DETERMINISTIC_SOURCE_REPLAY_MISMATCH", report.errors)

    def test_attestation_hmac_persists_across_restart(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, _, attestation = self.attestation(td)
            restarted = AdapterSynthesisService(ROOT, Path(td))
            loaded = restarted.load_attestation(Path(attestation["runtime_path"]))
            self.assertEqual(loaded["attestation_id"], attestation["attestation_id"])

    def test_attestation_digest_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            service, _, _, attestation = self.attestation(td)
            path = Path(attestation["runtime_path"])
            obj = json.loads(path.read_text())
            obj["attestation_sha256"] = "0" * 64
            obj.pop("hmac_sha256")
            obj["hmac_sha256"] = service._sign(dict(obj))
            path.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "digest"):
                service.load_attestation(path)

    def test_promotion_requires_explicit_approval(self):
        with tempfile.TemporaryDirectory() as td:
            service, _, record, attestation = self.attestation(td)
            with self.assertRaisesRegex(PermissionError, "explicit"):
                service.promote_candidate(
                    Path(attestation["runtime_path"]),
                    record["source_sha256"],
                    explicit_approval=False,
                )

    def test_promotion_requires_exact_sha(self):
        with tempfile.TemporaryDirectory() as td:
            service, _, _, attestation = self.attestation(td)
            with self.assertRaisesRegex(PermissionError, "SHA256"):
                service.promote_candidate(
                    Path(attestation["runtime_path"]),
                    "0" * 64,
                    explicit_approval=True,
                )

    def test_governed_handoff_is_review_only(self):
        with tempfile.TemporaryDirectory() as td:
            service, _, record, attestation = self.attestation(td)
            handoff = service.promote_candidate(
                Path(attestation["runtime_path"]),
                record["source_sha256"],
                explicit_approval=True,
                persist=True,
            )
            self.assertEqual(handoff["status"], "PHASE7_REVIEW_CANDIDATE")
            self.assertTrue(handoff["explicit_approval"])
            self.assertTrue(handoff["sha_bound"])
            self.assertFalse(handoff["repository_write_performed"])
            self.assertFalse(handoff["activation_transaction_created"])
            self.assertFalse(handoff["automatic_activation"])
            self.assertFalse(handoff["phase7_activation_transaction_eligible"])
            self.assertTrue(Path(handoff["source_path"]).is_file())
            self.assertTrue(
                Path(handoff["source_path"]).resolve().is_relative_to(
                    (Path(td) / "adapter_synthesis").resolve()
                )
            )

    def test_gateway_audit_records_all_phase8_writes(self):
        with tempfile.TemporaryDirectory() as td:
            service, _, record, attestation = self.attestation(td)
            service.promote_candidate(
                Path(attestation["runtime_path"]),
                record["source_sha256"],
                explicit_approval=True,
                persist=True,
            )
            audit = Path(td) / "gateway" / "audit_v1.jsonl"
            text = audit.read_text(encoding="utf-8")
            self.assertIn("adapter.synthesis.candidate.write", text)
            self.assertIn("adapter.verification.attestation.write", text)
            self.assertIn("adapter.promotion.handoff.write", text)

    def test_policy_bundle_binds_phase8_policies(self):
        manifest = load("policy_bundle_manifest_v1.json")
        for name in (
            "adapter_synthesis_policy_v1.json",
            "adapter_verification_profile_v1.json",
        ):
            self.assertTrue(manifest["files"][name]["required"])
            self.assertRegex(manifest["files"][name]["sha256"], r"^[a-f0-9]{64}$")


if __name__ == "__main__":
    unittest.main()
