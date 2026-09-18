import hashlib, json, tempfile, unittest
from pathlib import Path

from phoenix.autonomy import ActionRequest, AutonomyDecisionEngine, PolicyDecisionLog

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/"configs/phoenix"


def engine(log=None):
    return AutonomyDecisionEngine.from_repo(ROOT,log)


class TestAutonomyPolicyNorthStar(unittest.TestCase):
    def test_bundle_integrity_and_binding(self):
        e=engine()
        self.assertEqual(e.north_star["north_star_id"],"PHOENIX-NORTH-STAR")
        self.assertEqual(e.north_star["version"],"1.0.0")
        self.assertEqual(e.policy["version"],"2.5.0")
        self.assertTrue(e.bundle_sha256)

    def test_read_only_low_is_allow(self):
        d=engine().evaluate(ActionRequest("research.inspect","LOW",False,domain="research"),log=False)
        self.assertEqual(d.effect,"ALLOW")
        self.assertTrue(d.execution_authorized)

    def test_low_risk_mutation_with_all_gates_is_authorized(self):
        d=engine().evaluate(ActionRequest(
            "autonomy.self_improvement.low_risk_evidence","LOW",True,
            domain="orchestration",
            paths=("docs/automation/autonomous_generated/self_improvement/x.md",),
            gates=("clean_synced","verified_backup","open_source_review","risk_low","allowlisted_path","audit_log"),
        ),log=False)
        self.assertEqual(d.effect,"ALLOW_WITH_GATES")
        self.assertTrue(d.execution_authorized)
        self.assertEqual(d.missing_gates,())

    def test_low_risk_mutation_missing_backup_is_not_authorized(self):
        d=engine().evaluate(ActionRequest(
            "documentation.update","LOW",True,
            paths=("docs/automation/autonomous_generated/x.md",),
            gates=("clean_synced","open_source_review","risk_low","allowlisted_path","audit_log"),
        ),log=False)
        self.assertEqual(d.effect,"ALLOW_WITH_GATES")
        self.assertFalse(d.execution_authorized)
        self.assertIn("verified_backup",d.missing_gates)

    def test_source_change_escalates(self):
        d=engine().evaluate(ActionRequest("source.modify","MEDIUM",True,domain="software",paths=("phoenix/x.py",)),log=False)
        self.assertEqual(d.effect,"ESCALATE")
        self.assertFalse(d.execution_authorized)

    def test_policy_change_escalates(self):
        d=engine().evaluate(ActionRequest("north_star.modify","MEDIUM",True,domain="governance",paths=("configs/phoenix/north_star_v1.json",)),log=False)
        self.assertEqual(d.effect,"ESCALATE")

    def test_external_permit_submission_escalates(self):
        d=engine().evaluate(ActionRequest("permit.submit","MEDIUM",True,domain="permits",external_effect=True),log=False)
        self.assertEqual(d.effect,"ESCALATE")

    def test_force_push_denied(self):
        d=engine().evaluate(ActionRequest("git.force_push","CRITICAL",True,domain="git",flags=("force_push",)),log=False)
        self.assertEqual(d.effect,"DENY")
        self.assertFalse(d.execution_authorized)

    def test_fabrication_denied(self):
        d=engine().evaluate(ActionRequest("evidence.generate","LOW",True,paths=("docs/automation/autonomous_generated/x.md",),flags=("fabricate_evidence",)),log=False)
        self.assertEqual(d.effect,"DENY")

    def test_professional_approval_denied(self):
        d=engine().evaluate(ActionRequest("professional.approve","HIGH",True,domain="structural"),log=False)
        self.assertEqual(d.effect,"DENY")

    def test_high_risk_denied(self):
        d=engine().evaluate(ActionRequest("unknown.high","HIGH",True),log=False)
        self.assertEqual(d.effect,"DENY")

    def test_unknown_mutation_fails_closed(self):
        d=engine().evaluate(ActionRequest("unknown.mutation","LOW",True,paths=("unknown/file.txt",)),log=False)
        self.assertEqual(d.effect,"DENY")
        self.assertEqual(d.rule_id,"DEFAULT_FAIL_CLOSED")

    def test_unknown_read_only_escalates(self):
        d=engine().evaluate(ActionRequest("unknown.read","MEDIUM",False),log=False)
        self.assertEqual(d.effect,"ESCALATE")

    def test_bib_exact_allowlist_can_be_gated(self):
        p="bib/PHOENIX_AUTO_SYNC/BIB_CURRENT_STATE.json"
        d=engine().evaluate(ActionRequest(
            "bib.auto_sync","LOW",True,domain="bib",paths=(p,),
            gates=("provenance","exact_allowlist","no_secret","audit_log"),
        ),log=False)
        self.assertEqual(d.effect,"ALLOW_WITH_GATES")
        self.assertTrue(d.execution_authorized)

    def test_unknown_bib_mutation_denied(self):
        d=engine().evaluate(ActionRequest(
            "bib.auto_sync","LOW",True,domain="bib",
            paths=("bib/PHOENIX_AUTO_SYNC/UNKNOWN.json",),
            gates=("provenance","exact_allowlist","no_secret","audit_log"),
        ),log=False)
        self.assertEqual(d.effect,"DENY")

    def test_decision_contains_provenance(self):
        d=engine().evaluate(ActionRequest("research.inspect","LOW",False),log=False)
        self.assertEqual(d.north_star_version,"1.0.0")
        self.assertEqual(d.policy_version,"2.5.0")
        self.assertTrue(d.policy_bundle_sha256)

    def test_decision_log_is_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            log=PolicyDecisionLog(Path(td)/"decisions.jsonl")
            e=engine(log)
            d=e.evaluate(ActionRequest("research.inspect","LOW",False))
            rows=(Path(td)/"decisions.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows),1)
            obj=json.loads(rows[0])
            self.assertEqual(obj["decision"]["decision_id"],d.decision_id)
            self.assertEqual(obj["decision"]["policy_version"],"2.5.0")

    def test_tampered_bundle_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            c=root/"configs/phoenix"
            c.mkdir(parents=True)
            for name in ("north_star_v1.json","autonomy_policy_v2.json","policy_bundle_manifest_v1.json"):
                (c/name).write_bytes((CFG/name).read_bytes())
            with (c/"north_star_v1.json").open("a",encoding="utf-8") as f:
                f.write("\n ")
            with self.assertRaises(RuntimeError):
                AutonomyDecisionEngine.from_repo(root)

    def test_schemas_parse_and_are_draft_2020_12(self):
        for name in ("north_star_v1.schema.json","autonomy_policy_v2.schema.json"):
            data=json.loads((CFG/name).read_text(encoding="utf-8"))
            self.assertEqual(data["$schema"],"https://json-schema.org/draft/2020-12/schema")

    def test_machine_contract_requires_central_engine_and_deny_default(self):
        ns=engine().north_star["machine_contract"]
        self.assertTrue(ns["central_decision_engine_required_for_mutations"])
        self.assertEqual(ns["mutation_default_effect"],"DENY")
        self.assertTrue(ns["fail_closed"])

if __name__=="__main__":
    unittest.main()
